import json
import time
from typing import Any, Dict
import logging
import uuid
import os
from typing import List, Dict, Any, Tuple
import ast
import copy
from arklex.env.env import Env
import janus
from dotenv import load_dotenv
from difflib import SequenceMatcher

from langchain_core.runnables import RunnableLambda
import langsmith as ls
from openai import OpenAI
from langchain_openai import ChatOpenAI


from arklex.orchestrator.task_graph import TaskGraph
from arklex.env.tools.utils import ToolGenerator
from arklex.orchestrator.NLU.nlu import SlotFilling
from arklex.orchestrator.prompts import RESPOND_ACTION_NAME, RESPOND_ACTION_FIELD_NAME, REACT_INSTRUCTION
from arklex.types import EventType, StreamType
from arklex.utils.graph_state import ConvoMessage, OrchestratorMessage, MessageState, StatusEnum, BotConfig, Slot
from arklex.utils.utils import init_logger, truncate_string, format_chat_history, format_truncated_chat_history
from arklex.orchestrator.NLU.nlu import NLU
from arklex.utils.trace import TraceRunName, format_meta
from arklex.utils.model_config import MODEL
from arklex.utils.model_provider_config import PROVIDER_MAP
from arklex.env.planner.function_calling import aimessage_to_dict


load_dotenv()
logger = logging.getLogger(__name__)


class AgentOrg:
    def __init__(self, config, env: Env, **kwargs):
        if isinstance(config, dict):
            self.product_kwargs = config
        else:
            self.product_kwargs = json.load(open(config))
        self.user_prefix = "user"
        self.worker_prefix = "assistant"
        self.environment_prefix = "tool"
        self.__eos_token = "\n"
        self.task_graph = TaskGraph("taskgraph", self.product_kwargs)
        self.env = env

    def generate_next_step(
        self, messages: List[Dict[str, Any]], text:str
    ) -> Tuple[Dict[str, Any], str, float]:
        llm = PROVIDER_MAP.get(MODEL['llm_provider'], ChatOpenAI)(
                    model=MODEL["model_type_or_path"],
                    temperature = 0.0,
                )
        if MODEL['llm_provider'] == 'gemini':
            messages = [
                ("system",str(messages[0]['content']),),
                ("human", ""),
            ]
        elif MODEL['llm_provider'] == 'anthropic':
            messages = [
            ("human",str(messages[0]['content']),),
        ]
        res = llm.invoke(messages)        
        message = aimessage_to_dict(res)
        action_str = message['content'].split("Action:")[-1].strip()
        try:
            action_parsed = json.loads(action_str)
        except json.JSONDecodeError:
            # this is a hack
            logger.warning(f"Failed to parse action: {action_str}, choose respond action")
            action_parsed = {
                "name": RESPOND_ACTION_NAME,
                "arguments": {RESPOND_ACTION_FIELD_NAME: action_str},
            }
        if action_parsed.get("name"):
            action = action_parsed["name"]
        else:
            logger.warning(f"Failed to parse action: {action_str}, choose respond action")
            action = RESPOND_ACTION_NAME
        # issues with getting response_cost using langchain, set to 0.0 for now
        return message, action, 0.0


    def get_response(self, inputs: dict, stream_type: StreamType = None, message_queue: janus.SyncQueue = None) -> Dict[str, Any]:
        text = inputs["text"]
        chat_history = inputs["chat_history"]
        params = inputs["parameters"]
        params["timing"] = {}
        chat_history_copy = copy.deepcopy(chat_history)
        chat_history_copy.append({"role": self.user_prefix, "content": text})
        chat_history_str = format_chat_history(chat_history_copy)
        dialog_states = params.get("dialog_states", {})
        if dialog_states:
            params["dialog_states"] = {tool: [Slot(**slot_data) for slot_data in slots] for tool, slots in dialog_states.items()}
        else:
            params["dialog_states"] = {}
        metadata = params.get("metadata", {})
        metadata["chat_id"] = metadata.get("chat_id", str(uuid.uuid4()))
        metadata["turn_id"] = metadata.get("turn_id", 0) + 1
        metadata["tool_response"] = []
        params["metadata"] = metadata
        params["history"] = params.get("history", [])
        if not params["history"]:
            params["history"] = copy.deepcopy(chat_history_copy)
        else:
            params["history"].append(chat_history_copy[-2])
            params["history"].append(chat_history_copy[-1])


        ##### TaskGraph Chain
        taskgraph_inputs = {
            "text": text,
            "chat_history_str": chat_history_str,
            "parameters": params  ## TODO: different params for different components
        }
        dt = time.time()
        taskgraph_chain = RunnableLambda(self.task_graph.get_node) | RunnableLambda(self.task_graph.postprocess_node)
        node_info, params = taskgraph_chain.invoke(taskgraph_inputs, same_turn=False)
        params["timing"]["taskgraph"] = time.time() - dt
        logger.info("=============node_info=============")
        logger.info(f"The first node info is : {node_info}") # {'name': 'MessageWorker', 'attribute': {'value': 'If you are interested, you can book a calendly meeting https://shorturl.at/crFLP with us. Or, you can tell me your phone number, email address, and name; our expert will reach out to you soon.', 'direct': False, 'slots': {"<name>": {<attributes>}}}}
        node_status = params.get("node_status", {})
        params["node_status"] = node_status

        with ls.trace(name=TraceRunName.TaskGraph, inputs={"taskgraph_inputs": taskgraph_inputs}) as rt:
            rt.end(
                outputs={
                    "metadata": params.get("metadata"),
                    "timing": params.get("timing", {}),
                    "curr_node": {
                        "id": params.get("curr_node"),
                        "name": node_info.get("name"),
                        "attribute": node_info.get("attribute")
                    },
                    "curr_global_intent": params.get("curr_pred_intent"),
                    "dialog_states": params.get("dialog_states"),
                    "node_status": params.get("node_status")}, 
                metadata={"chat_id": metadata.get("chat_id"), "turn_id": metadata.get("turn_id")}
            )

        # Direct response
        node_attribute = node_info["attribute"]
        if node_attribute["value"].strip():
            if node_attribute.get("direct_response"):                    
                return_response = {
                    "answer": node_attribute["value"],
                    "parameters": params
                }
                # Change the dialog_states from Class object to dict
                if params.get("dialog_states"):
                    params["dialog_states"] = {tool: [s.model_dump() for s in slots] for tool, slots in params["dialog_states"].items()}
                if node_attribute["type"] == "multiple-choice":
                    return_response["choice_list"] = node_attribute["choice_list"]
                return return_response

        # Tool/Worker
        user_message = ConvoMessage(history=chat_history_str, message=text)
        orchestrator_message = OrchestratorMessage(message=node_info["attribute"]["value"], attribute=node_info["attribute"])
        sys_instruct = "You are a " + self.product_kwargs["role"] + ". " + self.product_kwargs["user_objective"] + self.product_kwargs["builder_objective"] + self.product_kwargs["intro"] + self.product_kwargs.get("opt_instruct", "")
        logger.info("=============sys_instruct=============")
        logger.info(sys_instruct)
        bot_config = BotConfig(
            bot_id=self.product_kwargs.get("bot_id", "default"),
            version=self.product_kwargs.get("version", "default"),
            language=self.product_kwargs.get("language", "EN"),
            bot_type=self.product_kwargs.get("bot_type", "presalebot"),
            available_workers=self.product_kwargs.get("workers", [])
        )
        message_state = MessageState(
            sys_instruct=sys_instruct, 
            bot_config=bot_config,
            user_message=user_message, 
            orchestrator_message=orchestrator_message, 
            trajectory=params["history"], 
            message_flow=params.get("worker_response", {}).get("message_flow", ""), 
            slots=params.get("dialog_states"),
            metadata={"chat_id": metadata.get("chat_id"), "turn_id": metadata.get("turn_id"), "tool_response": []},
            is_stream=True if stream_type is not None else False,
            message_queue=message_queue
        )
        
        response_state, params = self.env.step(node_info["id"], message_state, params)
        
        logger.info(f"{response_state=}")
        params = format_meta(response_state, params, node_info)

        with ls.trace(name=TraceRunName.ExecutionResult, inputs={"message_state": message_state}) as rt:
            rt.end(
                outputs={"metadata": params.get("metadata"), **response_state}, 
                metadata={"chat_id": metadata.get("chat_id"), "turn_id": metadata.get("turn_id")}
            )

        # ReAct framework to decide whether return to user or continue
        FINISH = False
        count = 0
        max_count = 5
        while not FINISH:
            # if the last response is from the assistant with content(which means not from tool or worker but from function calling response), 
            # then directly return the response otherwise it will continue to the next node but treat the previous response has been return to user.
            if response_state.get("trajectory", []) \
                and response_state["trajectory"][-1]["role"] == "assistant" \
                and response_state["trajectory"][-1]["content"]: 
                response_state["response"] = response_state["trajectory"][-1]["content"]
                break
            
            # If the max_count is reached, then break the loop
            if count >= max_count:
                logger.info("Max count reached, break the ReAct loop")
                break
            count += 1
            
            # If the current node is not complete, then no need to continue to the next node
            node_status = params.get("node_status", {})
            curr_node = params.get("curr_node", None)
            status = node_status.get(curr_node, StatusEnum.COMPLETE.value)
            if status == StatusEnum.INCOMPLETE.value:
                break

            node_info, params = taskgraph_chain.invoke(taskgraph_inputs, same_turn=True)
            logger.info("=============node_info=============")
            logger.info(f"The while node info is : {node_info}")
            message_state["orchestrator_message"] = OrchestratorMessage(message=node_info["attribute"]["value"], attribute=node_info["attribute"])
            if node_info["id"] not in self.env.workers and node_info["id"] not in self.env.tools:
                message_state = MessageState(
                    sys_instruct=sys_instruct, 
                    user_message=user_message, 
                    orchestrator_message=orchestrator_message, 
                    trajectory=params["history"], 
                    message_flow=params.get("worker_response", {}).get("message_flow", ""), 
                    slots=params.get("dialog_states"),
                    metadata={"chat_id": metadata.get("chat_id"), "turn_id": metadata.get("turn_id"), "tool_response": []},
                    is_stream=True if stream_type is not None else False,
                    message_queue=message_queue
                )
                
                action, response_state, msg_history = self.env.planner.execute(message_state, params["history"])
                # TODO Add planner response to the metadata
                params["history"] = msg_history
                if action == RESPOND_ACTION_NAME:
                    FINISH = True
                else:
                    tool_response = {}
            else:
                if node_info["id"] in self.env.tools:
                    node_actions = [{"name": self.env.id2name[node_info["id"]], "arguments": self.env.tools[node_info["id"]]["execute"]().info}]
                elif node_info["id"] in self.env.workers:
                    node_actions = [{"name": self.env.id2name[node_info["id"]], "description": self.env.workers[node_info["id"]]["execute"]().description}]
                
                # If the Default Worker enters the loop, it is the default node. It may call the RAG worker and no information in the context (tool response) can be used.
                if node_info["id"] == self.env.name2id["DefaultWorker"]:
                    logger.info("Skip the DefaultWorker in ReAct framework because it is the default node and may call the RAG worker (context cannot be used)")
                    action = RESPOND_ACTION_NAME
                    FINISH = True
                    break
                # If the Message Worker enters the loop, ReAct framework cannot make a good decision between the MessageWorker and the RESPOND action.
                elif node_info["id"] == self.env.name2id["MessageWorker"]:
                    logger.info("Skip ReAct framework because it is hard to distinguish between the MessageWorker and the RESPOND action")
                    message_state["response"] = "" # clear the response cache generated from the previous steps in the same turn
                    message_state["metadata"] = {"chat_id": metadata.get("chat_id"), "turn_id": metadata.get("turn_id"), "tool_response": []}
                    response_state, params = self.env.step(self.env.name2id["MessageWorker"], message_state, params)
                    params = format_meta(response_state, params, node_info)
                    FINISH = True
                    break
                action_spaces = node_actions
                response_msg = truncate_string(response_state.get("message_flow", "") or response_state.get("response", ""))
                action_spaces.append({"name": RESPOND_ACTION_NAME, "arguments": {RESPOND_ACTION_FIELD_NAME: response_msg}})
                truncated_params_history_str = format_truncated_chat_history(params["history"])
                prompt = REACT_INSTRUCTION.format(
                    conversation_record=truncated_params_history_str,
                    available_tools=json.dumps(action_spaces),
                    task=node_info["attribute"].get("task", "None"),
                )
                logger.info(f"React instruction: {prompt}")
                messages: List[Dict[str, Any]] = [
                    {"role": "system", "content": prompt}
                ]
                _, action, _ = self.generate_next_step(messages, text)
                action_name_list = [action_space["name"] for action_space in action_spaces]
                action_simi_score = [SequenceMatcher(None, action, action_name).ratio() for action_name in action_name_list]
                action = action_name_list[action_simi_score.index(max(action_simi_score))]
                logger.info("Predicted action: " + action)
                if action == RESPOND_ACTION_NAME:
                    FINISH = True
                else:
                    message_state["response"] = "" # clear the response cache generated from the previous steps in the same turn
                    message_state["metadata"] = {"chat_id": metadata.get("chat_id"), "turn_id": metadata.get("turn_id"), "tool_response": []}
                    response_state, params = self.env.step(self.env.name2id[action], message_state, params)
                    params = format_meta(response_state, params, node_info)
        if not response_state.get("response", ""):
            logger.info("No response from the ReAct framework, do context generation")
            tool_response = {}
            if stream_type is None:
                response_state = ToolGenerator.context_generate(response_state)
            else:
                response_state = ToolGenerator.stream_context_generate(response_state)
            params = format_meta(response_state, params, node_info=None)
        
        response = response_state.get("response", "")
        # params["metadata"]["tool_response"] = {}
        if params.get("dialog_states"):
            params["dialog_states"] = {tool: [s.model_dump() for s in slots] for tool, slots in params["dialog_states"].items()}
        # TODO: params["metadata"]["worker"] is not serialization, make it empty for now
        params["metadata"]["worker"] = {}
        # TODO: refomat the tool_response in chatbot repo
        # for item in params["metadata"]["tool_response"]:
        #     if milvus_id in item:
        #         params["tool_response"] = item[milvus_id]
        # params["tool_response"] = tool_response
        output = {
            "answer": response,
            "parameters": params
        }

        with ls.trace(name=TraceRunName.OrchestResponse) as rt:
            rt.end(
                outputs={"metadata": params.get("metadata"), **output},
                metadata={"chat_id": metadata.get("chat_id"), "turn_id": metadata.get("turn_id")}
            )

        return output

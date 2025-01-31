import json
import time
from typing import Any, Dict
import logging
import uuid
import os
from typing import List, Dict, Any, Tuple
import ast
import copy
from agentorg.env.env import Env
import janus
from dotenv import load_dotenv

from langchain_core.runnables import RunnableLambda
import langsmith as ls
from openai import OpenAI
from litellm import completion

from agentorg.orchestrator.task_graph import TaskGraph
from agentorg.env.tools.utils import ToolGenerator
from agentorg.orchestrator.NLU.nlu import SlotFilling
from agentorg.orchestrator.prompts import RESPOND_ACTION_NAME, RESPOND_ACTION_FIELD_NAME, REACT_INSTRUCTION
from agentorg.types import EventType, StreamType
from agentorg.utils.graph_state import ConvoMessage, OrchestratorMessage, MessageState, StatusEnum, BotConfig
from agentorg.utils.utils import init_logger, format_chat_history
from agentorg.orchestrator.NLU.nlu import NLU
from agentorg.utils.trace import TraceRunName
from agentorg.utils.model_config import MODEL


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
        self, messages: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], str, float]:
        res = completion(
                messages=messages,
                model=MODEL["model_type_or_path"],
                custom_llm_provider="openai",
                temperature=0.0
            )
        message = res.choices[0].message
        action_str = message.content.split("Action:")[-1].strip()
        try:
            action_parsed = json.loads(action_str)
        except json.JSONDecodeError:
            # this is a hack
            action_parsed = {
                "name": RESPOND_ACTION_NAME,
                "arguments": {RESPOND_ACTION_FIELD_NAME: action_str},
            }
        assert "name" in action_parsed
        assert "arguments" in action_parsed
        action = action_parsed["name"]
        return message.model_dump(), action, res._hidden_params["response_cost"]


    def get_response(self, inputs: dict, stream_type: StreamType = None, message_queue: janus.SyncQueue = None) -> Dict[str, Any]:
        text = inputs["text"]
        chat_history = inputs["chat_history"]
        params = inputs["parameters"]
        params["timing"] = {}
        chat_history.append({"role": self.user_prefix, "content": text})
        chat_history_str = format_chat_history(chat_history)
        params["dialog_states"] = params.get("dialog_states", [])
        metadata = params.get("metadata", {})
        metadata["chat_id"] = metadata.get("chat_id", str(uuid.uuid4()))
        metadata["turn_id"] = metadata.get("turn_id", 0) + 1
        metadata["tool_response"] = {}
        params["metadata"] = metadata
        params["history"] = params.get("history", [])
        if not params["history"]:
            params["history"] = copy.deepcopy(chat_history)
        else:
            params["history"].append(chat_history[-2])
            params["history"].append(chat_history[-1])

        ##### Model safety checking
        # check the response, decide whether to give template response or not
        client = OpenAI()
        text = inputs["text"]
        moderation_response = client.moderations.create(input=text).model_dump()
        is_flagged = moderation_response["results"][0]["flagged"]
        if is_flagged:
            return_response = {
                "answer": self.product_kwargs["safety_response"],
                "parameters": params,
                "has_follow_up": True
            }
            return return_response

        ##### TaskGraph Chain
        taskgraph_inputs = {
            "text": text,
            "chat_history_str": chat_history_str,
            "parameters": params  ## TODO: different params for different components
        }
        dt = time.time()
        taskgraph_chain = RunnableLambda(self.task_graph.get_node) | RunnableLambda(self.task_graph.postprocess_node)
        node_info, params = taskgraph_chain.invoke(taskgraph_inputs)
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
            metadata=params.get("metadata"),
            is_stream=True if stream_type is not None else False,
            message_queue=message_queue
        )
        
        response_state, params = self.env.step(node_info["id"], message_state, params)
        
        logger.info(f"{response_state=}")

        tool_response = params.get("metadata", {}).get("tool_response", {})
        params["metadata"]["tool_response"] = {}

        with ls.trace(name=TraceRunName.ExecutionResult, inputs={"message_state": message_state}) as rt:
            rt.end(
                outputs={"metadata": params.get("metadata"), **response_state}, 
                metadata={"chat_id": metadata.get("chat_id"), "turn_id": metadata.get("turn_id")}
            )

        # ReAct framework to decide whether return to user or continue
        FINISH = False
        while not FINISH:
            # if the last response is from the assistant with content(which means not from tool or worker but from function calling response), 
            # then directly return the response otherwise it will continue to the next node but treat the previous response has been return to user.
            if response_state.get("trajectory", []) \
                and response_state["trajectory"][-1]["role"] == "assistant" \
                and response_state["trajectory"][-1]["content"]: 
                response_state["response"] = response_state["trajectory"][-1]["content"]
                break
            node_info, params = taskgraph_chain.invoke(taskgraph_inputs)
            logger.info("=============node_info=============")
            logger.info(f"The while node info is : {node_info}")
            if node_info["id"] not in self.env.workers and node_info["id"] not in self.env.tools:
                message_state = MessageState(
                    sys_instruct=sys_instruct, 
                    user_message=user_message, 
                    orchestrator_message=orchestrator_message, 
                    trajectory=params["history"], 
                    message_flow=params.get("worker_response", {}).get("message_flow", ""), 
                    slots=params.get("dialog_states"),
                    metadata=params.get("metadata"),
                    is_stream=True if stream_type is not None else False,
                    message_queue=message_queue
                )
                
                action, response_state, msg_history = self.env.planner.execute(message_state, params["history"])
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
                action_spaces = node_actions
                action_spaces.append({"name": RESPOND_ACTION_NAME, "arguments": {RESPOND_ACTION_FIELD_NAME: response_state.get("message_flow", "") or response_state.get("response", "")}})
                logger.info("Action spaces: " + json.dumps(action_spaces))
                params_history_str = format_chat_history(params["history"])
                logger.info(f"{params_history_str=}")
                prompt = (
                    sys_instruct + "\n#Available tools\n" + json.dumps(action_spaces) + REACT_INSTRUCTION + "\n\n" + "Conversations:\n" + params_history_str + "Your current task is: " + node_info["attribute"].get("task", "") + "\nThougt:\n"
                )
                messages: List[Dict[str, Any]] = [
                    {"role": "system", "content": prompt}
                ]
                _, action, _ = self.generate_next_step(messages)
                logger.info("Predicted action: " + action)
                if action == RESPOND_ACTION_NAME:
                    FINISH = True
                else:
                    message_state["response"] = "" # clear the response cache generated from the previous steps in the same turn
                    response_state, params = self.env.step(self.env.name2id[action], message_state, params)
                    tool_response = params.get("metadata", {}).get("tool_response", {})

        if not response_state.get("response", ""):
            logger.info("No response from the ReAct framework, do context generation")
            tool_response = {}
            if stream_type is None:
                response_state = ToolGenerator.context_generate(response_state)
            else:
                response_state = ToolGenerator.stream_context_generate(response_state)

        response = response_state.get("response", "")
        params["metadata"]["tool_response"] = {}
        # TODO: params["metadata"]["worker"] is not serialization, make it empty for now
        params["metadata"]["worker"] = {}
        params["tool_response"] = tool_response
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

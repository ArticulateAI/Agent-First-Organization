import logging
from typing import Any, Iterator, Union

from langgraph.graph import StateGraph, START
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from agentorg.env.workers.worker import BaseWorker, register_worker
from agentorg.env.prompts import load_prompts
from agentorg.types import EventType
from agentorg.utils.utils import chunk_string
from agentorg.utils.graph_state import MessageState
from agentorg.utils.model_config import MODEL


logger = logging.getLogger(__name__)


@register_worker
class MessageWorker(BaseWorker):

    description = "The worker that used to deliver the message to the user, either a question or provide some information."

    def __init__(self):
        super().__init__()
        self.llm = ChatOpenAI(model=MODEL["model_type_or_path"], timeout=30000)
        self.action_graph = self._create_action_graph()

    def generator(self, state: MessageState) -> MessageState:
        # get the input message
        user_message = state['user_message']
        orchestrator_message = state['orchestrator_message']
        message_flow = state.get('response', "") + "\n" + state.get("message_flow", "")

        # get the orchestrator message content
        orch_msg_content = orchestrator_message.message
        orch_msg_attr = orchestrator_message.attribute
        direct_response = orch_msg_attr.get('direct_response', False)
        if direct_response:
            state["message_flow"] = ""
            state["response"] = orch_msg_content
            return state
        
        prompts = load_prompts(state["bot_config"])
        if message_flow and message_flow != "\n":
            prompt = PromptTemplate.from_template(prompts["message_flow_generator_prompt"])
            input_prompt = prompt.invoke({"sys_instruct": state["sys_instruct"], "message": orch_msg_content, "formatted_chat": user_message.history, "initial_response": message_flow})
        else:
            prompt = PromptTemplate.from_template(prompts["message_generator_prompt"])
            input_prompt = prompt.invoke({"sys_instruct": state["sys_instruct"], "message": orch_msg_content, "formatted_chat": user_message.history})
        logger.info(f"Prompt: {input_prompt.text}")
        chunked_prompt = chunk_string(input_prompt.text, tokenizer=MODEL["tokenizer"], max_length=MODEL["context"])
        final_chain = self.llm | StrOutputParser()
        answer = final_chain.invoke(chunked_prompt)

        state["message_flow"] = ""
        state["response"] = answer
        return state
    
    def choose_generator(self, state: MessageState):
        if state["is_stream"]:
            return "stream_generator"
        return "generator"
    
    def stream_generator(self, state: MessageState) -> MessageState:
        # get the input message
        user_message = state['user_message']
        orchestrator_message = state['orchestrator_message']
        message_flow = state.get('response', "") + "\n" + state.get("message_flow", "")

        # get the orchestrator message content
        orch_msg_content = orchestrator_message.message
        orch_msg_attr = orchestrator_message.attribute
        direct_response = orch_msg_attr.get('direct_response', False)
        if direct_response:
            state["message_flow"] = ""
            state["response"] = orch_msg_content
            return state
        
        prompts = load_prompts(state["bot_config"])
        if message_flow and message_flow != "\n":
            prompt = PromptTemplate.from_template(prompts["message_flow_generator_prompt"])
            input_prompt = prompt.invoke({"sys_instruct": state["sys_instruct"], "message": orch_msg_content, "formatted_chat": user_message.history, "initial_response": message_flow})
        else:
            prompt = PromptTemplate.from_template(prompts["message_generator_prompt"])
            input_prompt = prompt.invoke({"sys_instruct": state["sys_instruct"], "message": orch_msg_content, "formatted_chat": user_message.history})
        logger.info(f"Prompt: {input_prompt.text}")
        chunked_prompt = chunk_string(input_prompt.text, tokenizer=MODEL["tokenizer"], max_length=MODEL["context"])
        final_chain = self.llm | StrOutputParser()
        answer = ""
        for chunk in final_chain.stream(chunked_prompt):
            answer += chunk
            state["message_queue"].put({"event": EventType.CHUNK.value, "message_chunk": chunk})

        state["message_flow"] = ""
        state["response"] = answer
        return state

    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        # Add nodes for each worker
        workflow.add_node("generator", self.generator)
        workflow.add_node("stream_generator", self.stream_generator)
        # Add edges
        # workflow.add_edge(START, "generator")
        workflow.add_conditional_edges(START, self.choose_generator)
        return workflow

    def execute(self, msg_state: MessageState):
        graph = self.action_graph.compile()
        result = graph.invoke(msg_state)
        return result

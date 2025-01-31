import logging
import os
from typing import Any, Iterator, Union

from langgraph.graph import StateGraph, START
from langchain_openai import ChatOpenAI

from agentorg.env.workers.worker import BaseWorker, register_worker
from agentorg.utils.graph_state import MessageState
from agentorg.env.tools.utils import ToolGenerator
from agentorg.env.tools.RAG.retrievers.faiss_retriever import RetrieveEngine
from agentorg.utils.model_config import MODEL


logger = logging.getLogger(__name__)


@register_worker
class FaissRAGWorker(BaseWorker):

    description = "Answer the user's questions based on the company's internal documentations (unstructured text data), such as the policies, FAQs, and product information"

    def __init__(self,
                 # stream_ reponse is a boolean value that determines whether the response should be streamed or not.
                 # i.e in the case of RagMessageWorker it should be set to false.
                 stream_response: bool = True):
        super().__init__()
        self.action_graph = self._create_action_graph()
        self.llm = ChatOpenAI(model=MODEL["model_type_or_path"], timeout=30000)
        self.stream_response = stream_response

    def choose_tool_generator(self, state: MessageState):
        if self.stream_response and state["is_stream"]:
            return "stream_tool_generator"
        return "tool_generator"

    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        # Add nodes for each worker
        workflow.add_node("retriever", RetrieveEngine.faiss_retrieve)
        workflow.add_node("tool_generator", ToolGenerator.context_generate)
        workflow.add_node("stream_tool_generator", ToolGenerator.stream_context_generate)

        # Add edges
        workflow.add_edge(START, "retriever")
        workflow.add_conditional_edges(
            "retriever", self.choose_tool_generator)
        return workflow

    def execute(self, msg_state: MessageState):
        graph = self.action_graph.compile()
        result = graph.invoke(msg_state)
        return result

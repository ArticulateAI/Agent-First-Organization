import logging
import os

from langgraph.graph import StateGraph, START
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from agentorg.env.workers.worker import BaseWorker, register_worker
<<<<<<<< HEAD:agentorg/env/workers/hitl_worker.py
from agentorg.env.prompts import load_prompts
from agentorg.utils.utils import chunk_string
from agentorg.utils.graph_state import MessageState
========
from agentorg.utils.graph_state import MessageState
from agentorg.env.tools.utils import ToolGenerator
from agentorg.env.tools.RAG.retrievers.milvus_retriever import RetrieveEngine
>>>>>>>> 57d7e80df851c10d1032ed9f82d752ed9c567d31:agentorg/env/workers/milvus_rag_worker.py
from agentorg.utils.model_config import MODEL


logger = logging.getLogger(__name__)

 
class HitLWorker(BaseWorker):

<<<<<<<< HEAD:agentorg/env/workers/hitl_worker.py
    description = "The worker that used to deliver the message to the user, either a question or provide some information."
========
@register_worker
class MilvusRAGWorker(BaseWorker):

    description = "Answer the user's questions based on the company's internal documentations (unstructured text data), such as the policies, FAQs, and product information"
>>>>>>>> 57d7e80df851c10d1032ed9f82d752ed9c567d31:agentorg/env/workers/milvus_rag_worker.py

    def __init__(self,
                 # stream_ reponse is a boolean value that determines whether the response should be streamed or not.
                 # i.e in the case of RagMessageWorker it should be set to false.
                 stream_response: bool = True):
        super().__init__()
        self.llm = ChatOpenAI(model=MODEL["model_type_or_path"], timeout=30000)
<<<<<<<< HEAD:agentorg/env/workers/hitl_worker.py
        self.action_graph = self._create_action_graph()
        
    def hitl_input(hitl, start, outputs, timeout):
        workflow = StateGraph(MessageState)
        
        workflow.add_node("hitl", hitl)
        
========
        self.stream_response = stream_response

    def choose_tool_generator(self, state: MessageState):
        if self.stream_response and state["is_stream"]:
            return "stream_tool_generator"
        return "tool_generator"
>>>>>>>> 57d7e80df851c10d1032ed9f82d752ed9c567d31:agentorg/env/workers/milvus_rag_worker.py

    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        # Add nodes for each worker
<<<<<<<< HEAD:agentorg/env/workers/hitl_worker.py
        workflow.add_node("generator", self.generator)
        # Add edges
        workflow.add_edge(START, "generator")
========
        workflow.add_node("retriever", RetrieveEngine.milvus_retrieve)
        workflow.add_node("tool_generator", ToolGenerator.context_generate)
        workflow.add_node("stream_tool_generator", ToolGenerator.stream_context_generate)
        # Add edges
        workflow.add_edge(START, "retriever")
        workflow.add_conditional_edges(
            "retriever", self.choose_tool_generator)
>>>>>>>> 57d7e80df851c10d1032ed9f82d752ed9c567d31:agentorg/env/workers/milvus_rag_worker.py
        return workflow

    def execute(self, msg_state: MessageState):
        graph = self.action_graph.compile()
        result = graph.invoke(msg_state)
        return result

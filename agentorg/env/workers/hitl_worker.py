import logging

from langgraph.graph import StateGraph, START
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from agentorg.env.workers.worker import BaseWorker, register_worker
from agentorg.env.prompts import load_prompts
from agentorg.utils.utils import chunk_string
from agentorg.utils.graph_state import MessageState
from agentorg.utils.model_config import MODEL


logger = logging.getLogger(__name__)

 
class HitLWorker(BaseWorker):

    description = "The worker that used to deliver the message to the user, either a question or provide some information."

    def __init__(self):
        super().__init__()
        self.llm = ChatOpenAI(model=MODEL["model_type_or_path"], timeout=30000)
        self.action_graph = self._create_action_graph()
        
    def hitl_input(hitl, start, outputs, timeout):
        workflow = StateGraph(MessageState)
        
        workflow.add_node("hitl", hitl)
        

    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        # Add nodes for each worker
        workflow.add_node("generator", self.generator)
        # Add edges
        workflow.add_edge(START, "generator")
        return workflow

    def execute(self, msg_state: MessageState):
        graph = self.action_graph.compile()
        result = graph.invoke(msg_state)
        return result

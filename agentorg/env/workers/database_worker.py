import logging

from langgraph.graph import StateGraph, START
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from agentorg.env.workers.worker import BaseWorker, register_worker
from agentorg.env.prompts import load_prompts
from agentorg.env.tools.utils import ToolGenerator
from agentorg.env.tools.database.utils import DatabaseActions
from agentorg.utils.utils import chunk_string
from agentorg.utils.graph_state import MessageState
from agentorg.utils.model_config import MODEL



logger = logging.getLogger(__name__)


@register_worker
class DataBaseWorker(BaseWorker):

    description = "Help the user with actions related to customer support like a booking system with structured data, always involving search, insert, update, and delete operations."

    def __init__(self):
        self.llm = ChatOpenAI(model=MODEL["model_type_or_path"], timeout=30000)
        self.actions = {
            "SearchShow": "Search for shows", 
            "BookShow": "Book a show", 
            "CheckBooking": "Check details of booked show(s)",
            "CancelBooking": "Cancel a booking",
            "Others": "Other actions not mentioned above"
        }
        self.DBActions = DatabaseActions()
        self.action_graph = self._create_action_graph()

    def search_show(self, state: MessageState):
        return self.DBActions.search_show(state)
    
    def book_show(self, state: MessageState):
        return self.DBActions.book_show(state)
    
    def check_booking(self, state: MessageState):
        return self.DBActions.check_booking(state)
    
    def cancel_booking(self, state: MessageState):
        return self.DBActions.cancel_booking(state)

    def verify_action(self, msg_state: MessageState):
        user_intent = msg_state["orchestrator_message"].attribute.get("task", "")
        actions_info = "\n".join([f"{name}: {description}" for name, description in self.actions.items()])
        actions_name = ", ".join(self.actions.keys())

        prompts = load_prompts(msg_state["bot_config"])
        prompt = PromptTemplate.from_template(prompts["database_action_prompt"])
        input_prompt = prompt.invoke({"user_intent": user_intent, "actions_info": actions_info, "actions_name": actions_name})
        chunked_prompt = chunk_string(input_prompt.text, tokenizer=MODEL["tokenizer"], max_length=MODEL["context"])
        logger.info(f"Chunked prompt for deciding choosing DB action: {chunked_prompt}")
        final_chain = self.llm | StrOutputParser()
        try:
            answer = final_chain.invoke(chunked_prompt)
            for action_name in self.actions.keys():
                if action_name in answer:
                    logger.info(f"Chosen action in the database worker: {action_name}")
                    return action_name
            logger.info(f"Base action chosen in the database worker: Others")
            return "Others"
        except Exception as e:
            logger.error(f"Error occurred while choosing action in the database worker: {e}")
            return "Others"

        
    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        # Add nodes for each worker
        workflow.add_node("SearchShow", self.search_show)
        workflow.add_node("BookShow", self.book_show)
        workflow.add_node("CheckBooking", self.check_booking)
        workflow.add_node("CancelBooking", self.cancel_booking)
        workflow.add_node("Others", ToolGenerator.generate)
        workflow.add_node("tool_generator", ToolGenerator.context_generate)
        workflow.add_conditional_edges(START, self.verify_action)
        workflow.add_edge("SearchShow", "tool_generator")
        workflow.add_edge("BookShow", "tool_generator")
        workflow.add_edge("CheckBooking", "tool_generator")
        workflow.add_edge("CancelBooking", "tool_generator")
        return workflow

    def execute(self, msg_state: MessageState):
        self.DBActions.log_in()
        msg_state["slots"] = self.DBActions.init_slots(msg_state["slots"], msg_state["bot_config"])
        graph = self.action_graph.compile()
        result = graph.invoke(msg_state)
        return result

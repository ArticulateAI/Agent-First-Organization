import logging

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from arklex.env.workers.worker import BaseWorker, register_worker
from arklex.env.prompts import load_prompts
from arklex.utils.utils import chunk_string
from arklex.utils.graph_state import MessageState
from arklex.utils.model_config import MODEL
from arklex.utils.model_provider_config import PROVIDER_MAP


logger = logging.getLogger(__name__)


@register_worker
class DefaultWorker(BaseWorker):

    description = "Default worker decided by chat records if there is no specific worker for the user's query"

    def __init__(self):
        super().__init__()
        self.llm = PROVIDER_MAP.get(MODEL['llm_provider'], ChatOpenAI)(
            model=MODEL["model_type_or_path"], timeout=30000
        )
        self.base_choice = "MessageWorker"

    def _choose_worker(self, state: MessageState, limit=2):
        user_message = state['user_message']
        task = state["orchestrator_message"].attribute.get("task", "")
        self.available_workers = {id: resource for id, resource in state["metadata"]["worker"].items() if resource["name"] != "DefaultWorker"}
        self.name2id = {resource["name"]: id for id, resource in self.available_workers.items()}
        workers_info = "\n".join([f"{resource['name']}: {resource['description']}" for _, resource in self.available_workers.items()])
        workers_name = ", ".join(self.available_workers.keys())

        prompts = load_prompts(state["bot_config"])
        prompt = PromptTemplate.from_template(prompts["choose_worker_prompt"])
        input_prompt = prompt.invoke({"message": user_message.message, "formatted_chat": user_message.history, "task": task, "workers_info": workers_info, "workers_name": workers_name})
        chunked_prompt = chunk_string(input_prompt.text, tokenizer=MODEL["tokenizer"], max_length=MODEL["context"])
        final_chain = self.llm | StrOutputParser()
        while limit > 0:
            answer = final_chain.invoke(chunked_prompt)
            for worker_name in self.available_workers.keys():
                if worker_name in answer:
                    logger.info(f"Chosen worker for the default worker: {worker_name}")
                    worker_id = self.name2id[worker_name]
                    return worker_id
            limit -= 1
        logger.info(f"Base worker chosen for the default worker: {self.base_choice}")
        worker_id = self.name2id[self.base_choice]
        return worker_id
    
    def execute(self, msg_state: MessageState):
        worker_id = self._choose_worker(msg_state)
        worker = self.available_workers[worker_id]["execute"]()
        result = worker.execute(msg_state)
        return result

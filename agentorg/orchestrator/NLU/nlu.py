import requests
import logging
from dotenv import load_dotenv

import langsmith as ls

from agentorg.utils.trace import TraceRunName
from agentorg.utils.graph_state import Slots, Slot
from agentorg.orchestrator.NLU.api import nlu_openai, slotfilling_openai

load_dotenv()
logger = logging.getLogger(__name__)


class NLU:
    def __init__(self, url):
        self.url = url

    def execute(self, text:str, intents:dict, chat_history_str:str, metadata:dict) -> str:
        logger.info(f"candidates intents of NLU: {intents}")
        data = {
            "text": text,
            "intents": intents,
            "chat_history_str": chat_history_str
        }
        if self.url:
            logger.info(f"Using NLU API to predict the intent")
            response = requests.post(self.url + "/predict", json=data)
            if response.status_code == 200:
                results = response.json()
                pred_intent = results['intent']
                logger.info(f"pred_intent is {pred_intent}")
            else:
                pred_intent = "others"
                logger.error('Remote Server Error when predicting NLU')
        else:
            logger.info(f"Using NLU function to predict the intent")
            pred_intent = nlu_openai.predict(**data)
            logger.info(f"pred_intent is {pred_intent}")

        with ls.trace(name=TraceRunName.NLU, inputs=data) as rt:
            rt.end(
                outputs=pred_intent,
                metadata={"chat_id": metadata.get("chat_id"), "turn_id": metadata.get("turn_id")}
            )
        return pred_intent
    

class SlotFilling:
    def __init__(self, url):
        self.url = url

    def execute(self, slots:list, chat_history_str:str, metadata: dict) -> dict:
        logger.info(f"extracted slots: {slots}")
        if not slots: return []
        
        data = {
            "slots": [slot.dict() for slot in slots],
            "chat_history_str": chat_history_str
        }
        if self.url:
            logger.info(f"Using Slot Filling API to predict the slots")
            response = requests.post(self.url + "/predict", json=data)
            if response.status_code == 200:
                pred_slots = response.json()
                logger.info(f"The raw pred_slots is {pred_slots}")
                pred_slots = [Slot(**pred_slot) for pred_slot in pred_slots]
                logger.info(f"pred_slots is {pred_slots}")
            else:
                pred_slots = slots
                logger.error('Remote Server Error when predicting Slot Filling')
        else:
            logger.info(f"Using Slot Filling function to predict the slots")
            pred_slots = slotfilling_openai.predict(**data).slots
            # pred_slots = [Slot(**pred_slot) for pred_slot in pred_slots]
            logger.info(f"pred_slots is {pred_slots}")
        with ls.trace(name=TraceRunName.SlotFilling, inputs=data) as rt:
            rt.end(
                outputs=pred_slots,
                metadata={"chat_id": metadata.get("chat_id"), "turn_id": metadata.get("turn_id")}
            )
        return pred_slots

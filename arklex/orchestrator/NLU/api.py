import sys
import os
import json
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[3]))

import logging
import string

from openai.lib._parsing import parse_chat_completion
from openai._types import NOT_GIVEN
import litellm
from litellm import completion
from fastapi import FastAPI, Response

from arklex.utils.graph_state import Slots, Slot, Verification
from dotenv import load_dotenv
load_dotenv()

from arklex.utils.utils import format_messages_by_provider
from arklex.utils.model_config import MODEL
import google.generativeai as genai


logger = logging.getLogger(__name__)

SYSTEM_PROMPT_NLU = """According to the conversation, decide what is the user's intent in the last turn? \nHere are the definitions for each intent:\n{definition}\nHere are some sample utterances from user that indicate each intent:\n{exemplars}\nConversation:\n{formatted_chat}\n\nOnly choose from the following options.\n{intents_choice}\n\nAnswer:
"""

class NLUModelAPI ():
    def __init__(self):
        self.user_prefix = "user"
        self.assistant_prefix = "assistant"

    def get_response(self, sys_prompt, model, response_format="text", debug_text="none",  text=""):
        logger.info(f"gpt system_prompt for {debug_text} is \n{sys_prompt}")
        dialog_history = [{"role": "system", "content": sys_prompt}]
        litellm.modify_params=True
        if model['llm_provider'] == 'gemini':
            genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            llm = genai.GenerativeModel(
                f"models/{model['model_type_or_path']}",
                system_instruction=sys_prompt,
                 generation_config=genai.GenerationConfig(
                temperature = 0.7, candidate_count = 1, response_mime_type = ' application/json' if response_format == "json" else 'text/plain'
                ))
            response = llm.generate_content(" ").text
        else:
            res = completion(
                    model=model["model_type_or_path"],
                    custom_llm_provider=model["llm_provider"],
                    response_format={"type": "json_object"} if response_format=="json" else {"type": "text"},
                    **format_messages_by_provider(dialog_history, text),
                    n=1,
                    temperature = 0.7,
                )
            response = res.choices[0].message.content
            if model['llm_provider'] == 'anthropic':
                    response_data = json.loads(response)
                    response = response_data.get('intent', '')

        logger.info(f"response for {debug_text} is \n{response}")
        return response

    def format_input(self, intents, chat_history_str) -> str:
        """Format input text before feeding it to the model."""
        intents_choice, definition_str, exemplars_str = "", "", ""
        idx2intents_mapping = {}
        multiple_choice_index = dict(enumerate(string.ascii_lowercase))
        count = 0
        for intent_k, intent_v in intents.items():
            if len(intent_v) == 1:
                intent_name = intent_k
                idx2intents_mapping[multiple_choice_index[count]] = intent_name
                definition = intent_v[0].get("attribute", {}).get("definition", "")
                sample_utterances = intent_v[0].get("attribute", {}).get("sample_utterances", [])

                if definition:
                    definition_str += (
                        f"{multiple_choice_index[count]}) {intent_name}: {definition}\n"
                    )
                if sample_utterances:
                    exemplars = "\n".join(sample_utterances)
                    exemplars_str += (
                        f"{multiple_choice_index[count]}) {intent_name}: \n{exemplars}\n"
                    )
                intents_choice += f"{multiple_choice_index[count]}) {intent_name}\n"

                count += 1

            else:
                for idx, intent in enumerate(intent_v):
                    intent_name = f'{intent_k}__<{idx}>'
                    idx2intents_mapping[multiple_choice_index[count]] = intent_name
                    definition = intent.get("attribute", {}).get("definition", "")
                    sample_utterances = intent.get("attribute", {}).get("sample_utterances", [])

                    if definition:
                        definition_str += (
                            f"{multiple_choice_index[count]}) {intent_name}: {definition}\n"
                        )
                    if sample_utterances:
                        exemplars = "\n".join(sample_utterances)
                        exemplars_str += (
                            f"{multiple_choice_index[count]}) {intent_name}: \n{exemplars}\n"
                        )
                    intents_choice += f"{multiple_choice_index[count]}) {intent_name}\n"

                    count += 1

        system_prompt = SYSTEM_PROMPT_NLU.format(
            definition=definition_str,
            exemplars=exemplars_str,
            intents_choice=intents_choice,
            formatted_chat=chat_history_str,
        )
        return system_prompt, idx2intents_mapping

    def predict(
        self,
        text,
        intents,
        chat_history_str,
        model
    ) -> str:

        system_prompt, idx2intents_mapping = self.format_input(
            intents, chat_history_str
        )
        response = self.get_response(
            system_prompt,model, debug_text="get intent", text=text
        )
        logger.info(f"postprocessed intent response: {response}")
        try:
            pred_intent_idx = response.split(")")[0]
            pred_intent = idx2intents_mapping[pred_intent_idx]
        except:
            pred_intent = response.strip().lower()
        logger.info(f"postprocessed intent response: {pred_intent}")
        return pred_intent


class SlotFillModelAPI():
    def __init__(self):
        self.user_prefix = "user"
        self.assistant_prefix = "assistant"

    def get_response(self, sys_prompt,model, debug_text="none", text=" ", format=Slots):
        logger.info(f"gpt system_prompt for {debug_text} is \n{sys_prompt}")
        dialog_history = [{"role": "system", "content": sys_prompt}]
        res = completion(
            model=model["model_type_or_path"],
            custom_llm_provider=model["llm_provider"],
            response_format=format,
            **format_messages_by_provider(dialog_history, text, model),
            n=1,
            temperature = 0.7,
        )
        res.choices[0].message.refusal = None       
        parsed = parse_chat_completion(response_format=format,
                                    input_tools = NOT_GIVEN,
                                 chat_completion=res)
        
        response = parsed.choices[0].message
        if (response.refusal):
            return None
        logger.info(f"response for {debug_text} is \n{response.parsed}")
        return response.parsed

    def format_input(self, slots: Slots, chat_history_str) -> str:
        """Format input text before feeding it to the model."""
        system_prompt = f"Given the conversation and definition of each dialog state, update the value of following dialogue states.\nDialogue Statues:\n{slots}\nConversation:\n{chat_history_str}\n\n"
        return system_prompt

    def predict(
        self,
        slots,
        chat_history_str,
        model
    ):
        slots = [Slot(**slot_data) for slot_data in slots]
        system_prompt = self.format_input(
            slots, chat_history_str
        )
        user_input =  chat_history_str.splitlines()[-1].split('user:')[-1].strip()
        response = self.get_response(
            system_prompt,model, debug_text="get slots", text=user_input
        )
        if not response:
            logger.info(f"Failed to update dialogue states")
            return slots
        logger.info(f"Updated dialogue states: {response}")
        return response
    
    def verify(
        self,
        slot: dict,
        chat_history_str,
        model
    ) -> Verification:
        reformat_slot = {key: value for key, value in slot.items() if key in ["name", "type", "value", "enum", "description", "required"]}
        system_prompt = f"Given the conversation, definition and extracted value of each dialog state, decide whether the following dialog states values need further verification from the user. Verification is needed for expressions which may cause confusion. If it is an accurate information extracted, no verification is needed. If there is a list of enum value, which means the value has to be chosen from the enum list. Only Return boolean value: True or False. \nDialogue Statues:\n{reformat_slot}\nConversation:\n{chat_history_str}\n\n"
        response = self.get_response(
            system_prompt, model,debug_text="verify slots", format=Verification
        )
        if not response: # no need to verification, we want to make sure it is really confident that we need to ask the question again
            logger.info(f"Failed to verify dialogue states")
            return Verification(verification_needed=False, thought="No need to verify")
        logger.info(f"Verified dialogue states: {response}")
        return response


app = FastAPI()
nlu_api = NLUModelAPI()
slotfilling_api = SlotFillModelAPI()


@app.post("/nlu/predict")
def predict(data: dict, res: Response):
    logger.info(f"Received data: {data}")
    pred_intent = nlu_api.predict(**data)

    logger.info(f"pred_intent: {pred_intent}")
    return {"intent": pred_intent}

@app.post("/slotfill/predict")
def predict(data: dict, res: Response):
    logger.info(f"Received data: {data}")
    results = slotfilling_api.predict(**data)

    logger.info(f"pred_slots: {results.slots}")
    return results.slots

@app.post("/slotfill/verify")
def verify(data: dict, res: Response):
    logger.info(f"Received data: {data}")
    verify_needed = slotfilling_api.verify(**data)

    logger.info(f"verify_needed: {verify_needed}")
    return verify_needed
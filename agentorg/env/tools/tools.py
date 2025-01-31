import os
import logging
import json
import uuid
import ast
import inspect

from agentorg.utils.graph_state import MessageState, StatusEnum, Slot
from agentorg.orchestrator.NLU.nlu import SlotFilling
from agentorg.utils.utils import format_chat_history


logger = logging.getLogger(__name__)

    
def register_tool(desc, slots=[], outputs=[], isComplete=lambda x: True):
    current_file_dir = os.path.dirname(__file__)
    def inner(func):
        file_path = inspect.getfile(func)
        relative_path = os.path.relpath(file_path, current_file_dir)
        # reformat the relative path to replace / with -, and remove .py, because the function calling in openai only allow the function name match the patter the pattern '^[a-zA-Z0-9_-]+$'
        relative_path = relative_path.replace("/", "-").replace(".py", "")
        key = f"{relative_path}-{func.__name__}"
        tool = lambda : Tool(func, key, desc, slots, outputs, isComplete)
        return tool
    return inner

class Tool:
    def __init__(self, func, name, description, slots, outputs, isComplete):
        self.func = func
        self.name = name
        self.description = description
        self.output = outputs
        self.slotfillapi: SlotFilling = None
        self.info = self.get_info(slots)
        self.slots = self._format_slots(slots)
        self.isComplete = isComplete

    def _format_slots(self, slots):
        format_slots = []
        for slot in slots:
            format_slots.append(Slot(
                name=slot["name"], 
                type=slot["type"], 
                value="", 
                description=slot["description"], 
                prompt=slot["prompt"], 
                required=slot.get("required", False)
            ))
        return format_slots

    def get_info(self, slots):
        self.properties = {}
        for slot in slots:
            self.properties[slot["name"]] = {k: v for k, v in slot.items() if k != "name" and k != "required"}
        required = [slot["name"] for slot in slots if slot.get("required", False)]
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.properties,
                    "required": required,
                },
            },
        }
        
    def init_slotfilling(self, slotfillapi: SlotFilling):
        self.slotfillapi = slotfillapi
        
    def preprocess(self, state: MessageState, **fixed_args):
        response = "error"
        max_tries = 3
        while max_tries > 0 and "error" in response:
            chat_history_str = format_chat_history(state["trajectory"])
            slots : list[Slot] = self.slotfillapi.execute(self.slots, chat_history_str, state["metadata"])
            logger.info(f'{slots=}')
            # if slot.value is not empty for all slots, then execute the tool
            if all([slot.value for slot in slots if slot.required]):
                logger.info("all slots filled")
                for slot in slots:
                    if slot.type in ["list", "dict", "array"]:
                        try:
                            # Try to parse as JSON first
                            slot.value = json.loads(slot.value)
                        except json.JSONDecodeError:
                            # If JSON decoding fails, fallback to evaluating Python-like literals
                            try:
                                slot.value = ast.literal_eval(slot.value)
                            except (ValueError, SyntaxError):
                                raise ValueError(f"Unable to parse slot value: {slot.value}")
                kwargs = {slot.name: slot.value for slot in slots}
                combined_kwargs = {**kwargs, **fixed_args}
                response = self.func(**combined_kwargs)
                logger.info(f"Tool {self.name} response: {response}")
                call_id = str(uuid.uuid4())
                state["trajectory"].append({
                    'content': None, 
                    'role': 'assistant', 
                    'tool_calls': [
                        {
                            'function': {
                                'arguments': json.dumps(kwargs), 
                                'name': self.name
                            }, 
                            'id': call_id, 
                            'type': 'function'
                        }
                    ], 
                    'function_call': None
                })
                state["trajectory"].append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": self.name,
                    "content": response
                })
                if "error" in response:
                    max_tries -= 1
                    continue
                state["status"] = StatusEnum.COMPLETE.value if self.isComplete(response) else StatusEnum.INCOMPLETE.value
            else:
                # tool_response is the slot.prompt of the first slot where slot.value is empty
                for slot in slots:
                    if not slot.value:
                        response = slot.prompt
                        break
                state["status"] = StatusEnum.INCOMPLETE.value
                break
        state["message_flow"] = response
        return state

    def execute(self, state: MessageState, **fixed_args):
        state = self.preprocess(state, **fixed_args)
        ## postprocess if any
        ## Currently, the value of the tool is stored and returned in state["message_flow"]
        return state
    
    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"{self.__class__.__name__}"
    
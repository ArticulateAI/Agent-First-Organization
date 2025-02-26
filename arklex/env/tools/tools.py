import os
import logging
import json
import uuid
import ast
import inspect

from arklex.env.exceptions import FunctionCallError
from arklex.utils.graph_state import MessageState, StatusEnum, Slot
from arklex.orchestrator.NLU.nlu import SlotFilling
from arklex.utils.utils import format_chat_history


logger = logging.getLogger(__name__)

    
def register_tool(desc, slots=[], outputs=[], isComplete=lambda x: True):
    current_file_dir = os.path.dirname(__file__)
    def inner(func):
        file_path = inspect.getfile(func)
        relative_path = os.path.relpath(file_path, current_file_dir)
        # reformat the relative path to replace / and \\ with -, and remove .py, because the function calling in openai only allow the function name match the patter the pattern '^[a-zA-Z0-9_-]+$'
        # different file paths format in Windows and linux systems
        relative_path = relative_path.replace("/", "-").replace("\\", "-").replace(".py", "")
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
                enum=slot.get("enum", []),
                description=slot["description"], 
                prompt=slot["prompt"], 
                required=slot.get("required", False),
                verified=False
            ))
        return format_slots

    def get_info(self, slots):
        self.properties = {}
        for slot in slots:
            self.properties[slot["name"]] = {k: v for k, v in slot.items() if k in ["type", "description", "prompt", "items"]}
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

    def _tool_call(self, func):
        """Perform tool call and return (response: string, is_successful: bool)"""
        try:
            response = func()
            return response, True
        except FunctionCallError as e:
            return str(e), False
        except Exception as e:
            logger.error("Unexpected error: " + str(e))
            return str(e), False
        
    def _execute(self, state: MessageState, **fixed_args):
        # if this tool has been called before, then load the previous slots status
        if state["slots"].get(self.name):
            self.slots = state["slots"][self.name]
        else:
            state["slots"][self.name] = self.slots
        response = "error"
        max_tries = 3
        while max_tries > 0 and "error" in response:
            chat_history_str = format_chat_history(state["trajectory"])
            slots : list[Slot] = self.slotfillapi.execute(self.slots, chat_history_str, state["metadata"])
            logger.info(f'{slots=}')
            if not all([slot.value and slot.verified for slot in slots if slot.required]):
                for slot in slots:
                    # if there is extracted slots values but haven't been verified
                    if slot.value and not slot.verified:
                        # check whether it verified or not
                        verification_needed, thought = self.slotfillapi.verify_needed(slot, chat_history_str, state["metadata"])
                        if verification_needed:
                            response = slot.prompt + "The reason is: " + thought
                            break
                        else:
                            slot.verified = True
                    # if there is no extracted slots values, then should prompt the user to fill the slot
                    if not slot.value:
                        response = slot.prompt
                        break
                
                state["status"] = StatusEnum.INCOMPLETE.value
                
            # if slot.value is not empty for all slots, and all the slots has been verified, then execute the function
            if all([slot.value and slot.verified for slot in slots if slot.required]):
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
                response, is_successful = self._tool_call(lambda: self.func(**combined_kwargs))
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
                if not is_successful or "error" in response: # TODO: remove the second condition, use custom exception only
                    max_tries -= 1
                    continue
                state["status"] = StatusEnum.COMPLETE.value \
                                if is_successful and self.isComplete(response) \
                                else StatusEnum.INCOMPLETE.value
                
        state["message_flow"] = response
        state["slots"][self.name] = slots
        return state

    def execute(self, state: MessageState, **fixed_args):
        state = self._execute(state, **fixed_args)
        ## postprocess if any
        ## Currently, the value of the tool is stored and returned in state["message_flow"]
        return state
    
    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"{self.__class__.__name__}"
    
    
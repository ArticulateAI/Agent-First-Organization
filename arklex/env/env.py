import os
import logging
import uuid
import importlib
from typing import Optional

from arklex.env.tools.tools import Tool
from arklex.env.planner.function_calling import FunctionCallingPlanner
from arklex.utils.graph_state import StatusEnum
from arklex.orchestrator.NLU.nlu import SlotFilling


logger = logging.getLogger(__name__)

class BaseResourceInitializer:
    @staticmethod
    def init_tools(tools):
        raise NotImplementedError

    @staticmethod
    def init_workers(workers):
        raise NotImplementedError
    
class DefaulResourceInitializer(BaseResourceInitializer):
    @staticmethod
    def init_tools(tools):
        # return dict of valid tools with name and description
        tool_registry = {}
        for tool in tools:
            tool_id = tool["id"]
            name = tool["name"]
            path = tool["path"]
            try: # try to import the tool to check its existance
                filepath = os.path.join("arklex.env.tools", path)
                module_name = filepath.replace(os.sep, ".").rstrip(".py")
                module = importlib.import_module(module_name)
                func = getattr(module, name)
            except Exception as e:
                logger.error(f"Tool {name} is not registered, error: {e}")
                continue
            tool_registry[tool_id] = {
                "name": func().name,
                "description": func().description,
                "execute": func,
                "fixed_args": tool.get("fixed_args", {}),
            }
        return tool_registry
    
    @staticmethod
    def init_workers(workers):
        worker_registry = {}
        for worker in workers:
            worker_id = worker["id"]
            name = worker["name"]
            path = worker["path"]
            try: # try to import the worker to check its existance
                filepath = os.path.join("arklex.env.workers", path)
                module_name = filepath.replace(os.sep, ".").rstrip(".py")
                module = importlib.import_module(module_name)
                func = getattr(module, name)
            except Exception as e:
                logger.error(f"Worker {name} is not registered, error: {e}")
                continue
            worker_registry[worker_id] = {
                "name": name,
                "description": func().description,
                "execute": func
            }
        return worker_registry

class Env():
    def __init__(self, tools, workers, slotsfillapi, resource_inizializer: Optional[BaseResourceInitializer] = None):
        if resource_inizializer is None:
            resource_inizializer = DefaulResourceInitializer()
        self.tools = resource_inizializer.init_tools(tools)
        self.workers = resource_inizializer.init_workers(workers)
        self.name2id = {resource["name"]: id for id, resource in {**self.tools, **self.workers}.items()}
        self.id2name = {id: resource["name"] for id, resource in {**self.tools, **self.workers}.items()}
        self.slotfillapi = self.initialize_slotfillapi(slotsfillapi)
        self.planner = FunctionCallingPlanner(
            tools_map=self.tools,
            name2id=self.name2id
        )

    def initialize_slotfillapi(self, slotsfillapi):
        return SlotFilling(slotsfillapi)

    def step(self, id, message_state, params):
        if id in self.tools:
            logger.info(f"{self.tools[id]['name']} tool selected")
            tool: Tool = self.tools[id]["execute"]()
            tool.init_slotfilling(self.slotfillapi)
            response_state = tool.execute(message_state, **self.tools[id]["fixed_args"])
            params["history"] = response_state.get("trajectory", [])
            params["dialog_states"] = response_state.get("slots", [])
            current_node = params.get("curr_node")
            params["node_status"][current_node] = response_state.get("status", StatusEnum.COMPLETE.value)
                
        elif id in self.workers:
            message_state["metadata"]["worker"] = self.workers
            logger.info(f"{self.workers[id]['name']} worker selected")
            worker = self.workers[id]["execute"]()
            response_state = worker.execute(message_state)

            # If message_state contains "planner_selected": True, remove this key and then invoke FunctionCallingPlanner;
            # otherwise, DefaultWorker selected and invoked candidate worker instead of planner, so continue as normal
            if response_state.pop("planner_selected", False): # Remove this flag if present in response_state
                logger.info("FunctionCallingPlanner selected by DefaultWorker")
                action, response_state, msg_history = self.planner.execute(message_state, params["history"])
            else:
                call_id = str(uuid.uuid4())
                params["history"].append({'content': None, 'role': 'assistant', 'tool_calls': [{'function': {'arguments': "", 'name': self.id2name[id]}, 'id': call_id, 'type': 'function'}], 'function_call': None})
                params["history"].append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": self.id2name[id],
                            "content": response_state["response"]
                })

        else:
            logger.info("planner selected")
            action, response_state, msg_history = self.planner.execute(message_state, params["history"])
        
        logger.info(f"Response state from {id}: {response_state}")
        return response_state, params

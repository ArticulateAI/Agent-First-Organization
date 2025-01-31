import os
import logging
import uuid
import importlib

from agentorg.env.tools.tools import Tool
from agentorg.env.planner.function_calling import FunctionCallingPlanner
from agentorg.utils.graph_state import StatusEnum
from agentorg.orchestrator.NLU.nlu import SlotFilling


logger = logging.getLogger(__name__)

class Env():
    def __init__(self, tools, workers, slotsfillapi):
        self.tools = self.initialize_tools(tools)
        self.workers = self.initialize_workers(workers)
        self.name2id = {resource["name"]: id for id, resource in {**self.tools, **self.workers}.items()}
        self.id2name = {id: resource["name"] for id, resource in {**self.tools, **self.workers}.items()}
        self.slotfillapi = self.initialize_slotfillapi(slotsfillapi)
        self.planner = FunctionCallingPlanner(
            tools_map=self.tools,
            name2id=self.name2id
        )

    def initialize_tools(self, tools):
        tool_registry = {}
        for tool in tools:
            id = tool["id"]
            name = tool["name"]
            path = tool["path"]
            filepath = os.path.join("agentorg.env.tools", path)
            module_name = filepath.replace(os.sep, ".").rstrip(".py")
            module = importlib.import_module(module_name)
            func = getattr(module, name)
            tool_registry[id] = {"name": func().name, "execute": func, "fixed_args": tool.get("fixed_args", {})}
        return tool_registry

    def initialize_workers(self, workers):
        worker_registry = {}
        for worker in workers:
            id = worker["id"]
            name = worker["name"]
            path = worker["path"]
            filepath = os.path.join("agentorg.env.workers", path)
            module_name = filepath.replace(os.sep, ".").rstrip(".py")
            module = importlib.import_module(module_name)
            func = getattr(module, name)
            worker_registry[id] = {"name": name, "execute": func, "description": func().description}
        return worker_registry
    
    def initialize_slotfillapi(self, slotsfillapi):
        return SlotFilling(slotsfillapi)

    def step(self, id, message_state, params):
        if id in self.tools:
            logger.info(f"{self.tools[id]['name']} tool selected")
            tool: Tool = self.tools[id]["execute"]()
            tool.init_slotfilling(self.slotfillapi)
            response_state = tool.execute(message_state, **self.tools[id]["fixed_args"])
            params["history"] = response_state.get("trajectory", [])
            current_node = params.get("curr_node")
            params["node_status"][current_node] = response_state.get("status", StatusEnum.COMPLETE.value)
                
        elif id in self.workers:
            message_state["metadata"]["worker"] = self.workers
            logger.info(f"{self.workers[id]['name']} worker selected")
            worker = self.workers[id]["execute"]()
            response_state = worker.execute(message_state)
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

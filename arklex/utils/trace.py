from enum import Enum
import copy

class TraceRunName(str, Enum):
    TaskGraph = "TaskGraph"
    ExecutionResult = "ExecutionResult"
    OrchestResponse = "OrchestResponse"
    NLU = "NLU"
    SlotFilling = "SlotFilling"


def format_meta(response_state, params, node_info=None):
    if not node_info:
        tool_info = None
        tool_input = None
    else:
        tool_info = node_info
        tool_input = response_state.get("slots", {})
        
    tool_output = response_state.get("response", "") or response_state.get("message_flow", "")
    tool_response = copy.deepcopy(response_state.get("metadata", {}).get("tool_response", {}))
    params["metadata"]["tool_response"].append({
        "tool_info": tool_info,
        "tool_input": tool_input,
        "tool_output": tool_output,
        "tool_inter": tool_response
    })
    return params
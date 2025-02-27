from typing import TypedDict, Annotated, Any, Optional, Union
import janus
from pydantic import BaseModel
from enum import Enum


### Bot-related classes
class BotConfig(BaseModel):
    bot_id: str
    version: str
    language: str
    bot_type: str


### Message-related classes

class ConvoMessage(BaseModel):
    history: str # it could be the whole original message or the summarization of the previous conversation from memory module
    message: str


class OrchestratorMessage(BaseModel):
    message: str
    attribute: dict


### Slot-related classes

class Slot(BaseModel):
    name: str
    type: Union[str, int, float, bool, None]
    value: Union[str, int, float, bool, None]
    enum: Optional[list[Union[str, int, float, bool, None]]]
    description: str
    prompt: str
    required: bool
    verified: bool


class Slots(BaseModel):
    slots: list[Slot]

# May not be needed
class SlotDetail(Slot):
    verified_value: str
    confirmed: bool

class Verification(BaseModel):
    thought: str
    verification_needed: bool


### Task status-related classes

class StatusEnum(Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class MessageState(TypedDict):
    # system configuration
    sys_instruct: str
    # bot configuration
    bot_config: BotConfig
    # input message
    user_message: ConvoMessage
    orchestrator_message: OrchestratorMessage
    # action trajectory
    trajectory: list[dict[str, any]]
    # message flow between different nodes
    message_flow: Annotated[str, "message flow between different nodes"]
    # final response
    response: str
    # task-related params
    status: StatusEnum
    slots: dict[str, list[Slot]]  # record the dialogue states of each action
    metadata: dict[str, any]
    # stream
    is_stream: bool
    message_queue: janus.SyncQueue
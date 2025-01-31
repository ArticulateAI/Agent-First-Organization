from typing import TypedDict, Annotated
import janus
from pydantic import BaseModel
from enum import Enum


### Bot-related classes
class BotConfig(BaseModel):
    bot_id: str
    version: str
    language: str
    bot_type: str
    available_workers: list[dict[str, str]]


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
    type: str
    value: str
    description: str
    prompt: str
    required: bool


class Slots(BaseModel):
    slots: list[Slot]


class SlotDetail(Slot):
    verified_value: str
    confirmed: bool


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
    slots: list[Slot]  # probably won't need anymore
    metadata: dict[str, any]
    # stream
    is_stream: bool
    message_queue: janus.SyncQueue
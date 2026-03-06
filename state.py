import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

STATE_PATH = os.path.join(os.path.dirname(__file__), "state_store", "agent_state.json")


class AgentState(Enum):
    IDLE = "idle"
    RESEARCHING = "researching"
    EMAILING_TOPICS = "emailing_topics"
    WAITING_FOR_REPLY = "waiting_for_reply"
    DRAFTING = "drafting"
    EMAILING_DRAFT = "emailing_draft"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentContext:
    state: AgentState = AgentState.IDLE
    topics: list = field(default_factory=list)
    selected_topic: Optional[str] = None
    tone: Optional[str] = None
    draft: Optional[str] = None
    topics_email_body: Optional[str] = None
    inbox_id: Optional[str] = None
    thread_subject: Optional[str] = None
    initial_message_count: int = 0
    started_at: Optional[str] = None
    last_poll_at: Optional[str] = None
    poll_count: int = 0
    max_polls: int = 60
    poll_interval_sec: int = 300

    def save(self):
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        data = {**self.__dict__, "state": self.state.value}
        with open(STATE_PATH, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> "AgentContext":
        if not os.path.exists(STATE_PATH):
            return cls()
        with open(STATE_PATH) as f:
            data = json.load(f)
        data["state"] = AgentState(data["state"])
        return cls(**data)

    def should_reset(self) -> bool:
        if self.state not in (AgentState.DONE, AgentState.ERROR):
            return False
        if not self.started_at:
            return True
        return self.started_at[:10] != datetime.now().strftime("%Y-%m-%d")

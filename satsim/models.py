"""Domain objects for the satellite camera data manager."""
from dataclasses import dataclass
from enum import Enum


class Importance(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class Picture:
    index: int
    take_at_min: int
    size_mb: int
    importance: Importance


@dataclass(frozen=True)
class Pass:
    start_min: int
    end_min: int
    speed_mb_per_min: int


class EventKind(Enum):
    TAKEN = "TAKEN"
    STORED = "STORED"
    SKIPPED = "SKIPPED"
    EVICTED = "EVICTED"
    SEND_START = "SEND_START"
    SEND_PROGRESS = "SEND_PROGRESS"
    SEND_COMPLETE = "SEND_COMPLETE"


@dataclass(frozen=True)
class Event:
    minute: int
    kind: EventKind
    picture_index: int
    detail: str = ""

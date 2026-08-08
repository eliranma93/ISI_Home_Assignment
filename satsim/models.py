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

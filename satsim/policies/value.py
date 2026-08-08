"""ValueFunction: the shared notion of a picture's worth, injected into both
StoragePolicy and DownlinkPolicy so eviction and transmission rank pictures on
the same scale."""
from abc import ABC, abstractmethod

from satsim.models import Picture


class ValueFunction(ABC):
    @abstractmethod
    def value_of(self, picture: Picture, now_min: int) -> int: ...

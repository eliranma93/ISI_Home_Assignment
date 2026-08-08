"""StoragePolicy: decides what happens when a picture arrives - admit, skip, or
evict other pictures to make room."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from satsim.models import Picture
from satsim.storage import Storage


@dataclass(frozen=True)
class Store:
    pass


@dataclass(frozen=True)
class Skip:
    reason: str


@dataclass(frozen=True)
class EvictThenStore:
    indices: tuple[int, ...]


Decision = Store | Skip | EvictThenStore


class StoragePolicy(ABC):
    @abstractmethod
    def on_arrival(self, incoming: Picture, storage: Storage, now_min: int) -> Decision: ...


class FitsOrSkipStorage(StoragePolicy):
    """Phase 2 placeholder: store the incoming picture if it fits in free space,
    otherwise skip it. Never evicts. Replaced in Phase 3."""

    def on_arrival(self, incoming: Picture, storage: Storage, now_min: int) -> Decision:
        if incoming.size_mb <= storage.free_mb():
            return Store()
        return Skip(reason=f"does not fit: needs {incoming.size_mb}MB, {storage.free_mb()}MB free")

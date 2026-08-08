"""StoragePolicy: decides what happens when a picture arrives - admit, skip, or
evict other pictures to make room."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from satsim.models import Importance, Picture
from satsim.policies.value import ValueFunction, sorted_ascending_by_density
from satsim.storage import Storage, StoredPicture


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


_IMPORTANCE_RANK = {Importance.LOW: 0, Importance.MEDIUM: 1, Importance.HIGH: 2}


class ImportanceThenAgeStorage(StoragePolicy):
    """Baseline: evict the lowest-importance pictures first, oldest first
    within a level, until the incoming picture fits. Ignores value density
    entirely - this is the naive policy the value-density approach exists
    to beat.
    """

    def on_arrival(self, incoming: Picture, storage: Storage, now_min: int) -> Decision:
        if incoming.size_mb <= storage.free_mb():
            return Store()

        ranked = sorted(
            storage.all(),
            key=lambda stored: (
                _IMPORTANCE_RANK[stored.picture.importance],
                stored.picture.take_at_min,
                stored.picture.index,
            ),
        )

        evict_indices: list[int] = []
        freed_mb = storage.free_mb()
        for stored in ranked:
            if freed_mb >= incoming.size_mb:
                break
            evict_indices.append(stored.picture.index)
            freed_mb += stored.picture.size_mb

        if freed_mb < incoming.size_mb:
            return Skip(reason="not enough storage even after evicting everything evictable")
        return EvictThenStore(indices=tuple(evict_indices))


class ValueDensityStorage(StoragePolicy):
    """GDS-derived eviction: rank stored pictures by value density ascending
    and evict the cheapest until the incoming picture fits, admitting only if
    its value exceeds the summed value of everything evicted to make room -
    absolute value, not density, since both sides occupy the same freed bytes.

    Classic GDS carries an inflation term L that rises every time something is
    evicted, so that a page evicted long ago and re-requested later isn't
    unfairly cheap next to pages evicted more recently - it compensates for
    repeated access to the same item over time. Every picture here is written
    once by the camera and read once by the ground station; there is no
    repeated access for L to correct for. Carrying it anyway would let a
    picture that has simply been sitting in storage the longest accumulate
    enough inflated "credit" to eventually outrank a freshly-arrived
    high-importance picture on density alone - an aging bug wearing an
    optimization's clothes. Omitted deliberately.
    """

    def __init__(self, value_function: ValueFunction):
        self._value_function = value_function

    def on_arrival(self, incoming: Picture, storage: Storage, now_min: int) -> Decision:
        if incoming.size_mb <= storage.free_mb():
            return Store()

        incoming_value = self._value_function.value_of(incoming, now_min)
        candidates = self._eviction_candidates(storage, now_min)

        evict_indices: list[int] = []
        evicted_value = 0
        freed_mb = storage.free_mb()
        for stored in candidates:
            if freed_mb >= incoming.size_mb:
                break
            evict_indices.append(stored.picture.index)
            evicted_value += self._value_function.value_of(stored.picture, now_min)
            freed_mb += stored.picture.size_mb

        if freed_mb < incoming.size_mb:
            return Skip(reason="not enough storage even after evicting everything evictable")
        if incoming_value > evicted_value:
            return EvictThenStore(indices=tuple(evict_indices))
        return Skip(reason=f"value {incoming_value} does not exceed eviction-set value {evicted_value}")

    def _eviction_candidates(self, storage: Storage, now_min: int) -> list[StoredPicture]:
        # A partially sent picture is only evicted if it is the only
        # candidate: rank every untouched picture ahead of every started one,
        # each group ordered by density ascending. See NOTES.md.
        untouched = [stored for stored in storage.all() if stored.sent_mb == 0]
        started = [stored for stored in storage.all() if stored.sent_mb > 0]
        return sorted_ascending_by_density(untouched, self._value_function, now_min) + sorted_ascending_by_density(
            started, self._value_function, now_min
        )

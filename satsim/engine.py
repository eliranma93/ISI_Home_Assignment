"""Simulator: owns the minute clock, drives arrivals and transmission, records events.

Arrivals are processed before transmission within the same minute, so a picture
taken at minute t is sendable starting at minute t. Passes are half-open
[start_min, end_min): the boundary minute end_min is not a transmitting minute.
"""
from satsim.models import Event, EventKind, Pass, Picture
from satsim.policies.downlink_policy import DownlinkPolicy, SendOrder
from satsim.policies.storage_policy import EvictThenStore, Skip, Store, StoragePolicy
from satsim.storage import Storage


class Simulator:
    def __init__(
        self,
        pictures: list[Picture],
        passes: list[Pass],
        storage: Storage,
        storage_policy: StoragePolicy,
        downlink_policy: DownlinkPolicy,
    ):
        self._pictures = pictures
        self._passes = passes
        self._storage = storage
        self._storage_policy = storage_policy
        self._downlink_policy = downlink_policy
        self._events: list[Event] = []

    def run(self) -> list[Event]:
        last_minute = self._last_relevant_minute()
        arrival_pos = 0
        for now in range(last_minute + 1):
            arrival_pos = self._process_arrivals(now, arrival_pos)
            self._process_transmission(now)
        return list(self._events)

    def _last_relevant_minute(self) -> int:
        candidates = [picture.take_at_min for picture in self._pictures]
        candidates += [window.end_min - 1 for window in self._passes]
        return max(candidates, default=0)

    def _process_arrivals(self, now: int, arrival_pos: int) -> int:
        while arrival_pos < len(self._pictures) and self._pictures[arrival_pos].take_at_min == now:
            picture = self._pictures[arrival_pos]
            self._record(now, EventKind.TAKEN, picture.index)
            self._admit(picture, now)
            arrival_pos += 1
        return arrival_pos

    def _admit(self, picture: Picture, now: int) -> None:
        decision = self._storage_policy.on_arrival(picture, self._storage, now)
        if isinstance(decision, Store):
            self._storage.add(picture)
            self._record(now, EventKind.STORED, picture.index)
        elif isinstance(decision, Skip):
            self._record(now, EventKind.SKIPPED, picture.index, decision.reason)
        elif isinstance(decision, EvictThenStore):
            for evict_index in decision.indices:
                self._storage.remove(evict_index)
                self._record(now, EventKind.EVICTED, evict_index, f"for #{picture.index}")
            self._storage.add(picture)
            self._record(now, EventKind.STORED, picture.index)

    def _process_transmission(self, now: int) -> None:
        active_pass = self._active_pass(now)
        if active_pass is None:
            return
        orders = self._downlink_policy.select(self._storage, active_pass.speed_mb_per_min, now)
        for order in orders:
            self._apply_send(order, now)

    def _active_pass(self, now: int) -> Pass | None:
        for window in self._passes:
            if window.start_min <= now < window.end_min:
                return window
        return None

    def _apply_send(self, order: SendOrder, now: int) -> None:
        stored = self._storage.get(order.picture_index)
        was_unstarted = stored.sent_mb == 0
        stored.sent_mb += order.send_mb
        detail = str(order.send_mb)
        if stored.sent_mb == stored.picture.size_mb:
            self._storage.remove(order.picture_index)
            self._record(now, EventKind.SEND_COMPLETE, order.picture_index, detail)
        elif was_unstarted:
            self._record(now, EventKind.SEND_START, order.picture_index, detail)
        else:
            self._record(now, EventKind.SEND_PROGRESS, order.picture_index, detail)

    def _record(self, minute: int, kind: EventKind, picture_index: int, detail: str = "") -> None:
        self._events.append(Event(minute=minute, kind=kind, picture_index=picture_index, detail=detail))

"""DownlinkPolicy: decides what to send during a pass and in what order,
within that minute's transmission budget."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from satsim.storage import Storage


@dataclass(frozen=True)
class SendOrder:
    picture_index: int
    send_mb: int


class DownlinkPolicy(ABC):
    @abstractmethod
    def select(self, storage: Storage, budget_mb: int, now_min: int) -> list[SendOrder]: ...


class ArrivalOrderDownlink(DownlinkPolicy):
    """Phase 2 placeholder: send stored pictures in arrival order (index order),
    filling the budget. Replaced in Phase 3."""

    def select(self, storage: Storage, budget_mb: int, now_min: int) -> list[SendOrder]:
        orders: list[SendOrder] = []
        remaining_budget = budget_mb
        for stored in sorted(storage.all(), key=lambda s: s.picture.index):
            if remaining_budget <= 0:
                break
            send_mb = min(stored.remaining_mb, remaining_budget)
            if send_mb > 0:
                orders.append(SendOrder(picture_index=stored.picture.index, send_mb=send_mb))
                remaining_budget -= send_mb
        return orders

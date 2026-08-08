"""DownlinkPolicy: decides what to send during a pass and in what order,
within that minute's transmission budget."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from satsim.models import Importance
from satsim.policies.value import ValueFunction, sorted_ascending_by_density
from satsim.storage import Storage


@dataclass(frozen=True)
class SendOrder:
    picture_index: int
    send_mb: int


class DownlinkPolicy(ABC):
    @abstractmethod
    def select(self, storage: Storage, budget_mb: int, now_min: int) -> list[SendOrder]: ...


_IMPORTANCE_RANK = {Importance.LOW: 0, Importance.MEDIUM: 1, Importance.HIGH: 2}


class ImportanceFirstAtomic(DownlinkPolicy):
    """Baseline: send highest-importance pictures first, whole or not at all -
    a picture that doesn't fit entirely in the remaining budget is skipped
    this window rather than split.
    """

    def select(self, storage: Storage, budget_mb: int, now_min: int) -> list[SendOrder]:
        ranked = sorted(
            storage.all(),
            key=lambda stored: (
                -_IMPORTANCE_RANK[stored.picture.importance],
                stored.picture.take_at_min,
                stored.picture.index,
            ),
        )

        orders: list[SendOrder] = []
        remaining_budget = budget_mb
        for stored in ranked:
            if stored.remaining_mb <= remaining_budget:
                orders.append(SendOrder(picture_index=stored.picture.index, send_mb=stored.remaining_mb))
                remaining_budget -= stored.remaining_mb
        return orders


class DensityFractionalDownlink(DownlinkPolicy):
    """Primary: fractional knapsack by value density descending - fill the
    budget with the highest-density pictures first, splitting the boundary
    picture across this window and the next via chunking-with-resume.

    This is provably optimal for delivered value-MB, and optimal for
    delivered value at all only because chunking-with-resume exists: without
    resume, a greedy fractional fill would count the split picture's partial
    bytes as delivered value even though a picture cut off mid-transmission
    that never gets to finish delivers nothing usable on the ground.
    """

    def __init__(self, value_function: ValueFunction):
        self._value_function = value_function

    def select(self, storage: Storage, budget_mb: int, now_min: int) -> list[SendOrder]:
        ranked_descending = list(reversed(sorted_ascending_by_density(storage.all(), self._value_function, now_min)))

        orders: list[SendOrder] = []
        remaining_budget = budget_mb
        for stored in ranked_descending:
            if remaining_budget <= 0:
                break
            send_mb = min(stored.remaining_mb, remaining_budget)
            if send_mb > 0:
                orders.append(SendOrder(picture_index=stored.picture.index, send_mb=send_mb))
                remaining_budget -= send_mb
        return orders

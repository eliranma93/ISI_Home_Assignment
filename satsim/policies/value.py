"""ValueFunction: the shared notion of a picture's worth, injected into both
StoragePolicy and DownlinkPolicy so eviction and transmission rank pictures on
the same scale."""
from abc import ABC, abstractmethod

from satsim.models import Importance, Picture
from satsim.storage import StoredPicture


class ValueFunction(ABC):
    @abstractmethod
    def value_of(self, picture: Picture, now_min: int) -> int: ...


class ImportanceValue(ValueFunction):
    """value(HIGH) = 100, value(MEDIUM) = 50, value(LOW) = 20. That is the whole class."""

    _VALUE_BY_IMPORTANCE = {Importance.HIGH: 100, Importance.MEDIUM: 50, Importance.LOW: 20}

    def value_of(self, picture: Picture, now_min: int) -> int:
        return self._VALUE_BY_IMPORTANCE[picture.importance]


def sorted_ascending_by_density(
    stored_pictures: list[StoredPicture], value_function: ValueFunction, now_min: int
) -> list[StoredPicture]:
    """Total order by value density (value / size_mb), cheapest first.

    Densities are compared by integer cross multiplication - a.value *
    b.size_mb vs b.value * a.size_mb - never as a float ratio - with the
    picture's input row index as the final, unique tie-breaker. This is the
    one place both StoragePolicy and DownlinkPolicy rank by density, so
    eviction and transmission can never drift onto different scales.
    """
    result: list[StoredPicture] = []
    for stored in stored_pictures:
        pos = len(result)
        while pos > 0 and _is_less_dense(stored, result[pos - 1], value_function, now_min):
            pos -= 1
        result.insert(pos, stored)
    return result


def _is_less_dense(a: StoredPicture, b: StoredPicture, value_function: ValueFunction, now_min: int) -> bool:
    value_a = value_function.value_of(a.picture, now_min)
    value_b = value_function.value_of(b.picture, now_min)
    left = value_a * b.picture.size_mb
    right = value_b * a.picture.size_mb
    if left != right:
        return left < right
    return a.picture.index < b.picture.index

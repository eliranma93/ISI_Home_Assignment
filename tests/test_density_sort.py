"""Direct unit tests for sorted_ascending_by_density (satsim/policies/value.py).
Out-of-plan addition - see docs/NOTES.md."""
import unittest

from satsim.models import Importance, Picture
from satsim.policies.value import ImportanceValue, sorted_ascending_by_density
from satsim.storage import StoredPicture


def _stored(index: int, size_mb: int, importance: Importance) -> StoredPicture:
    picture = Picture(index=index, take_at_min=0, size_mb=size_mb, importance=importance)
    return StoredPicture(picture=picture)


class DensitySortTests(unittest.TestCase):
    def setUp(self):
        self.value_function = ImportanceValue()

    def test_orders_ascending_by_density(self):
        cheap = _stored(1, size_mb=100, importance=Importance.LOW)  # 20/100 = 0.2
        mid = _stored(2, size_mb=50, importance=Importance.MEDIUM)  # 50/50  = 1.0
        dense = _stored(3, size_mb=10, importance=Importance.HIGH)  # 100/10 = 10.0

        ranked = sorted_ascending_by_density([mid, dense, cheap], self.value_function, now_min=0)

        self.assertEqual([stored.picture.index for stored in ranked], [1, 2, 3])

    def test_equal_density_breaks_tie_by_row_index(self):
        # medium at 100MB (50/100 = 0.5) and low at 40MB (20/40 = 0.5): equal density.
        higher_index = _stored(5, size_mb=100, importance=Importance.MEDIUM)
        lower_index = _stored(2, size_mb=40, importance=Importance.LOW)

        ranked = sorted_ascending_by_density([higher_index, lower_index], self.value_function, now_min=0)

        self.assertEqual([stored.picture.index for stored in ranked], [2, 5])

    def test_returns_new_list_without_mutating_input_order(self):
        dense = _stored(1, size_mb=10, importance=Importance.HIGH)  # 100/10 = 10.0
        cheap = _stored(2, size_mb=10, importance=Importance.LOW)  # 20/10  = 2.0
        original = [dense, cheap]

        ranked = sorted_ascending_by_density(original, self.value_function, now_min=0)

        self.assertEqual([stored.picture.index for stored in ranked], [2, 1])
        self.assertEqual([stored.picture.index for stored in original], [1, 2])


if __name__ == "__main__":
    unittest.main()

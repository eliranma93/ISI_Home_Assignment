"""Storage-policy edge cases: capacity limits and value-based eviction
(PLAN.md Phase 5, tests 1-3)."""
import tempfile
import unittest
from pathlib import Path

from satsim.models import EventKind
from tests.helpers import run_simulation


class StorageEvictionTests(unittest.TestCase):
    def test_picture_larger_than_capacity_is_skipped_once_never_stored(self):
        with tempfile.TemporaryDirectory() as tmp:
            events, storage, _, _ = run_simulation(
                Path(tmp), picture_rows=["5,150,high"], pass_rows=["10,20,50"], storage_mb=100
            )

        self.assertEqual([e for e in events if e.kind == EventKind.STORED], [])
        skipped = [e for e in events if e.kind == EventKind.SKIPPED]
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0].picture_index, 1)
        self.assertIsNone(storage.get(1))

    def test_higher_value_incoming_evicts_lower_value_and_stores(self):
        with tempfile.TemporaryDirectory() as tmp:
            events, storage, _, _ = run_simulation(
                Path(tmp),
                picture_rows=["1,80,low", "5,90,high"],
                pass_rows=["0,1,50"],
                storage_mb=100,
            )

        evicted = [e for e in events if e.kind == EventKind.EVICTED]
        stored_indices = [e.picture_index for e in events if e.kind == EventKind.STORED]
        self.assertEqual(len(evicted), 1)
        self.assertEqual(evicted[0].picture_index, 1)
        self.assertIn(2, stored_indices)
        self.assertIsNone(storage.get(1))
        self.assertIsNotNone(storage.get(2))

    def test_lower_value_incoming_is_skipped_incumbent_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            events, storage, _, _ = run_simulation(
                Path(tmp),
                picture_rows=["1,80,high", "5,90,low"],
                pass_rows=["0,1,50"],
                storage_mb=100,
            )

        self.assertEqual([e for e in events if e.kind == EventKind.EVICTED], [])
        skipped = [e for e in events if e.kind == EventKind.SKIPPED]
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0].picture_index, 2)
        self.assertIsNotNone(storage.get(1))


if __name__ == "__main__":
    unittest.main()

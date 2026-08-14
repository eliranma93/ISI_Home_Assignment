"""Picture taken after the last window closes: stored, reported as
unreachable (docs/PLAN.md Phase 5, test 7)."""
import tempfile
import unittest
from pathlib import Path

from satsim.models import EventKind
from satsim.report import unreachable_report
from tests.helpers import run_simulation

_SEND_KINDS = (EventKind.SEND_START, EventKind.SEND_PROGRESS, EventKind.SEND_COMPLETE)


class UnreachableTests(unittest.TestCase):
    def test_picture_taken_after_last_window_is_stored_and_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            events, storage, pictures, passes = run_simulation(
                Path(tmp), picture_rows=["20,50,high"], pass_rows=["5,10,100"], storage_mb=200
            )

        stored = [e for e in events if e.kind == EventKind.STORED]
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].picture_index, 1)
        self.assertEqual([e for e in events if e.kind in _SEND_KINDS], [])

        still_in_storage, never_sendable = unreachable_report(pictures, passes, storage)
        self.assertIn(1, [stored.picture.index for stored in still_in_storage])
        self.assertIn(1, [picture.index for picture in never_sendable])


if __name__ == "__main__":
    unittest.main()

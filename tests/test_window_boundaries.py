"""Half-open pass windows and chunked transmission with resume
(docs/PLAN.md Phase 5, tests 4-6)."""
import tempfile
import unittest
from pathlib import Path

from satsim.models import EventKind
from tests.helpers import run_simulation

_SEND_KINDS = (EventKind.SEND_START, EventKind.SEND_PROGRESS, EventKind.SEND_COMPLETE)


class WindowBoundaryTests(unittest.TestCase):
    def test_window_ends_mid_picture_partial_send_resumes_next_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            events, storage, _, _ = run_simulation(
                Path(tmp),
                picture_rows=["1,100,high"],
                pass_rows=["5,6,30", "10,11,100"],
                storage_mb=200,
            )

        send_by_minute_kind = {(e.minute, e.kind): e.detail for e in events if e.kind in _SEND_KINDS}
        self.assertEqual(send_by_minute_kind.get((5, EventKind.SEND_START)), "30")
        self.assertEqual(send_by_minute_kind.get((10, EventKind.SEND_COMPLETE)), "70")
        self.assertIsNone(storage.get(1))

    def test_picture_taken_at_window_start_is_sendable_same_minute(self):
        with tempfile.TemporaryDirectory() as tmp:
            events, _, _, _ = run_simulation(
                Path(tmp), picture_rows=["5,50,high"], pass_rows=["5,10,100"], storage_mb=200
            )

        complete = [e for e in events if e.kind == EventKind.SEND_COMPLETE]
        self.assertEqual(len(complete), 1)
        self.assertEqual(complete[0].minute, 5)

    def test_picture_taken_at_window_end_is_not_sendable_that_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            events, _, _, _ = run_simulation(
                Path(tmp),
                picture_rows=["10,50,high"],
                pass_rows=["5,10,100", "15,20,100"],
                storage_mb=200,
            )

        self.assertEqual([e for e in events if e.minute == 10 and e.kind in _SEND_KINDS], [])
        complete = [e for e in events if e.kind == EventKind.SEND_COMPLETE]
        self.assertEqual(len(complete), 1)
        self.assertEqual(complete[0].minute, 15)


if __name__ == "__main__":
    unittest.main()

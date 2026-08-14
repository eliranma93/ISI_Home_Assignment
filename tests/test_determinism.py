"""Determinism against the real dataset (docs/PLAN.md Phase 5, test 10)."""
import contextlib
import io
import unittest
from pathlib import Path

from main import main as run_cli

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_and_capture(argv: list[str]) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        run_cli(argv)
    return buffer.getvalue()


class DeterminismTests(unittest.TestCase):
    def test_real_dataset_produces_identical_output_twice(self):
        argv = ["--pictures", str(_REPO_ROOT / "pictures.csv"), "--passes", str(_REPO_ROOT / "passes.csv")]
        first = _run_and_capture(argv)
        second = _run_and_capture(argv)
        self.assertEqual(first, second)
        self.assertIn("Summary:", first)


if __name__ == "__main__":
    unittest.main()

"""CLI-level input edge cases: empty pictures.csv and malformed rows
(PLAN.md Phase 5, tests 8-9)."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from main import main as run_cli
from tests.helpers import PASSES_HEADER, PICTURES_HEADER, write_csv


class CsvValidationTests(unittest.TestCase):
    def test_empty_pictures_csv_is_a_clean_zeroed_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pictures_path = write_csv(tmp_path, "pictures.csv", PICTURES_HEADER, [])
            passes_path = write_csv(tmp_path, "passes.csv", PASSES_HEADER, ["5,10,50"])

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                exit_code = run_cli(["--pictures", str(pictures_path), "--passes", str(passes_path)])

        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("pictures taken:        0", output)
        self.assertIn("total value delivered: 0", output)

    def test_malformed_row_reports_every_error_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pictures_path = write_csv(
                tmp_path, "pictures.csv", PICTURES_HEADER, ["abc,46,high", "10,-5,high"]
            )
            passes_path = write_csv(tmp_path, "passes.csv", PASSES_HEADER, ["5,10,50"])

            stderr_buffer = io.StringIO()
            with contextlib.redirect_stderr(stderr_buffer):
                exit_code = run_cli(["--pictures", str(pictures_path), "--passes", str(passes_path)])

        self.assertNotEqual(exit_code, 0)
        errors = stderr_buffer.getvalue()
        self.assertIn("take_at_min is not an integer", errors)
        self.assertIn("size_mb must be > 0", errors)


if __name__ == "__main__":
    unittest.main()

"""Shared test scaffolding: write synthetic CSV fixtures and run the pipeline.
Not a test module itself - unittest discover ignores it (no test_ prefix)."""
from pathlib import Path

from satsim.csv_input import load_input
from satsim.engine import Simulator
from satsim.policies.downlink_policy import DensityFractionalDownlink
from satsim.policies.storage_policy import ValueDensityStorage
from satsim.policies.value import ImportanceValue
from satsim.storage import Storage

PICTURES_HEADER = "take_at_min,size_mb,importance\n"
PASSES_HEADER = "window_start_min,window_end_min,link_speed_mb_per_min\n"


def write_csv(directory: Path, filename: str, header: str, rows: list[str]) -> Path:
    path = directory / filename
    body = "\n".join(rows) + ("\n" if rows else "")
    path.write_text(header + body, encoding="utf-8")
    return path


def run_simulation(
    tmp_path: Path,
    picture_rows: list[str],
    pass_rows: list[str],
    storage_mb: int,
    storage_policy=None,
    downlink_policy=None,
):
    """Write picture_rows/pass_rows as CSVs, load and simulate with the
    primary policies by default. Returns (events, storage, pictures, passes)."""
    pictures_path = write_csv(tmp_path, "pictures.csv", PICTURES_HEADER, picture_rows)
    passes_path = write_csv(tmp_path, "passes.csv", PASSES_HEADER, pass_rows)
    pictures, passes = load_input(str(pictures_path), str(passes_path))

    value_function = ImportanceValue()
    storage = Storage(capacity_mb=storage_mb)
    simulator = Simulator(
        pictures=pictures,
        passes=passes,
        storage=storage,
        storage_policy=storage_policy or ValueDensityStorage(value_function),
        downlink_policy=downlink_policy or DensityFractionalDownlink(value_function),
    )
    events = simulator.run()
    return events, storage, pictures, passes

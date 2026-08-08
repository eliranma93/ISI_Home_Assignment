"""CLI entry point for the Satellite Camera Data Manager."""
import argparse
import sys

from satsim.csv_input import InputError, load_input
from satsim.engine import Simulator
from satsim.models import EventKind
from satsim.policies.downlink_policy import DensityFractionalDownlink, DownlinkPolicy, ImportanceFirstAtomic
from satsim.policies.storage_policy import ImportanceThenAgeStorage, StoragePolicy, ValueDensityStorage
from satsim.policies.value import ImportanceValue, ValueFunction
from satsim.storage import Storage

DEFAULT_STORAGE_MB = 512

# (header label, width, alignment) - shared between the header row and every data
# row so columns line up. DETAIL is appended separately, unpadded.
DUMP_COLUMNS = [
    ("MINUTE", 10, "<"),
    ("EVENT", 14, "<"),
    ("PIC", 5, "<"),
    ("SIZE", 6, ">"),
    ("IMPORTANCE", 11, "<"),
    ("TAKEN@", 10, "<"),
    ("STORAGE", 10, "<"),
]


def _format_dump_row(values: list[str]) -> str:
    cells = [f"{value:{align}{width}}" for value, (_, width, align) in zip(values, DUMP_COLUMNS)]
    return " ".join(cells)


def _build_storage_policy(name: str, value_function: ValueFunction) -> StoragePolicy:
    if name == "importance_age":
        return ImportanceThenAgeStorage()
    return ValueDensityStorage(value_function)


def _build_downlink_policy(name: str, value_function: ValueFunction) -> DownlinkPolicy:
    if name == "importance_first":
        return ImportanceFirstAtomic()
    return DensityFractionalDownlink(value_function)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Simulate one orbit of a satellite's camera, storage, and downlink.",
    )
    parser.add_argument("--pictures", required=True, help="Path to pictures.csv")
    parser.add_argument("--passes", required=True, help="Path to passes.csv")
    parser.add_argument(
        "--storage-mb",
        type=int,
        default=DEFAULT_STORAGE_MB,
        help=f"Storage capacity in MB (default: {DEFAULT_STORAGE_MB})",
    )
    parser.add_argument(
        "--storage-policy",
        choices=["importance_age", "value_density"],
        default="value_density",
        help="Admission/eviction policy (default: value_density)",
    )
    parser.add_argument(
        "--downlink-policy",
        choices=["importance_first", "density_fractional"],
        default="density_fractional",
        help="Downlink send-order policy (default: density_fractional)",
    )
    parser.add_argument(
        "--dump-events",
        action="store_true",
        help="Debug aid: print every raw Event record. Not the Phase 4 timeline report.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        pictures, passes = load_input(args.pictures, args.passes)
    except InputError as exc:
        for error in exc.errors:
            print(error, file=sys.stderr)
        return 1

    print("Satellite Camera Data Manager")
    print(f"  pictures file:    {args.pictures}")
    print(f"  passes file:      {args.passes}")
    print(f"  storage capacity: {args.storage_mb} MB")
    print(f"  storage policy:   {args.storage_policy}")
    print(f"  downlink policy:  {args.downlink_policy}")
    print(f"Loaded: {len(pictures)} pictures, {len(passes)} passes")

    value_function = ImportanceValue()
    storage = Storage(capacity_mb=args.storage_mb)
    simulator = Simulator(
        pictures=pictures,
        passes=passes,
        storage=storage,
        storage_policy=_build_storage_policy(args.storage_policy, value_function),
        downlink_policy=_build_downlink_policy(args.downlink_policy, value_function),
    )
    events = simulator.run()
    total_sent_mb = sum(
        int(event.detail)
        for event in events
        if event.kind in (EventKind.SEND_START, EventKind.SEND_PROGRESS, EventKind.SEND_COMPLETE)
    )
    print(
        f"Simulated: {len(events)} events, peak storage {storage.peak_used_mb}/{args.storage_mb} MB, "
        f"total sent {total_sent_mb} MB"
    )
    print("(full formatted timeline and summary report pending Phase 4)")

    if args.dump_events:
        pictures_by_index = {picture.index: picture for picture in pictures}
        header_values = [name for name, _, _ in DUMP_COLUMNS]
        print(_format_dump_row(header_values) + " DETAIL")

        used_mb = 0
        for event in events:
            picture = pictures_by_index[event.picture_index]
            if event.kind == EventKind.STORED:
                used_mb += picture.size_mb
            elif event.kind in (EventKind.EVICTED, EventKind.SEND_COMPLETE):
                used_mb -= picture.size_mb
            row_values = [
                f"[min {event.minute:03d}]",
                event.kind.value,
                f"#{event.picture_index:02d}",
                f"{picture.size_mb}MB",
                picture.importance.value,
                f"taken@{picture.take_at_min:03d}",
                f"{used_mb}/{args.storage_mb}MB",
            ]
            print(_format_dump_row(row_values) + " " + event.detail)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

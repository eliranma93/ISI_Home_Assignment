"""CLI entry point for the Satellite Camera Data Manager."""
import argparse
import sys

from debug_dump import print_dump_events
from satsim.csv_input import InputError, load_input
from satsim.engine import Simulator
from satsim.policies.downlink_policy import DensityFractionalDownlink, DownlinkPolicy, ImportanceFirstAtomic
from satsim.policies.storage_policy import ImportanceThenAgeStorage, StoragePolicy, ValueDensityStorage
from satsim.policies.value import ImportanceValue, ValueFunction
from satsim.report import build_summary, format_summary, format_timeline, format_unreachable, unreachable_report
from satsim.storage import Storage

DEFAULT_STORAGE_MB = 512


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
        "--quiet",
        action="store_true",
        help="Print only the summary block, for building a policy-comparison table.",
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

    if not args.quiet:
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

    if not args.quiet:
        for line in format_timeline(events, pictures, storage):
            print(line)

    summary = build_summary(events, pictures, storage, value_function)
    for line in format_summary(summary):
        print(line)

    if not args.quiet:
        still_in_storage, never_sendable = unreachable_report(pictures, passes, storage)
        for line in format_unreachable(still_in_storage, never_sendable):
            print(line)

    if args.dump_events:
        print_dump_events(events, pictures, args.storage_mb)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

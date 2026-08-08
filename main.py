"""CLI entry point for the Satellite Camera Data Manager."""
import argparse
import sys

from satsim.csv_input import InputError, load_input
from satsim.engine import Simulator
from satsim.models import EventKind
from satsim.policies.downlink_policy import ArrivalOrderDownlink
from satsim.policies.storage_policy import FitsOrSkipStorage
from satsim.storage import Storage

DEFAULT_STORAGE_MB = 512


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

    storage = Storage(capacity_mb=args.storage_mb)
    simulator = Simulator(
        pictures=pictures,
        passes=passes,
        storage=storage,
        storage_policy=FitsOrSkipStorage(),
        downlink_policy=ArrivalOrderDownlink(),
    )
    events = simulator.run()
    print(f"Simulated: {len(events)} events, peak storage {storage.peak_used_mb}/{args.storage_mb} MB")
    print("(policy selection and full report pending Phase 3/4 - placeholder policies used)")

    if args.dump_events:
        pictures_by_index = {picture.index: picture for picture in pictures}
        print(
            f"{'MINUTE':<10}{'EVENT':<15}{'PIC':<5}{'SIZE':>6}  {'IMPORTANCE':<11}{'TAKEN@':<12}"
            f"{'STORAGE':<16}DETAIL"
        )
        used_mb = 0
        for event in events:
            picture = pictures_by_index[event.picture_index]
            if event.kind in (EventKind.STORED,):
                used_mb += picture.size_mb
            elif event.kind in (EventKind.EVICTED, EventKind.SEND_COMPLETE):
                used_mb -= picture.size_mb
            print(
                f"[min {event.minute:03d}] {event.kind.value:<14} #{event.picture_index:02d}  "
                f"{picture.size_mb:>3}MB {picture.importance.value:<6} taken@{picture.take_at_min:03d}  "
                f"storage {used_mb:>3}/{args.storage_mb}MB  "
                f"{event.detail}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI entry point for the Satellite Camera Data Manager."""
import argparse
import sys

from satsim.csv_input import InputError, load_input

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
    print("(stub - simulation not yet implemented)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="solo-roll")
    parser.add_argument("--version", action="version", version=f"solo-roll {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = False  # will become True once subcommands land

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

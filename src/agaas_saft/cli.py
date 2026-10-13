"""A file/stdin in, one JSON report out. Exit 0/1/2 means valid/invalid/error."""

import argparse
import json
import sys

from . import __version__
from .accounts import validate_accounts
from .report import Report
from .validation import MAX_INPUT_BYTES, capabilities, validate_saft


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        # Do not print caller-provided strings or paths in machine-readable diagnostics.
        report = Report("invocation")
        report.add("USAGE", "Invalid arguments; see agaas-saft --help.", error=True)
        print(json.dumps(report.to_dict()))
        raise SystemExit(2)


def _read(path):
    if path == "-":
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        with open(path, "rb") as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise OverflowError
    return data


def main(argv=None):
    parser = Arguments(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("info", help="Print supported checks and upstream revision as JSON")
    saft = commands.add_parser("validate", help="Validate SAF-T Financial XML")
    saft.add_argument("file", help="XML file or - for stdin")
    saft.add_argument("--schema-version", default="1.40")
    saft.add_argument("--codelist-year", type=int)
    accounts = commands.add_parser("accounts", help="Check local-to-NS-4102 account mappings")
    accounts.add_argument("file", help="Mapping JSON file or - for stdin")
    accounts.add_argument("--catalogue", required=True, help="Licensed catalogue JSON file")
    args = parser.parse_args(argv)
    if args.command == "info":
        print(json.dumps({**capabilities(), "validator_version": __version__}))
        return 0
    try:
        if args.command == "validate":
            report = validate_saft(
                _read(args.file),
                schema_version=args.schema_version,
                codelist_year=args.codelist_year,
            )
        elif args.catalogue == "-":
            report = Report("accounts")
            report.add(
                "USAGE", "The catalogue must be a file; stdin is reserved for mappings.", error=True
            )
        else:
            report = validate_accounts(_read(args.file), catalogue=_read(args.catalogue))
    except OSError:
        report = Report(args.command)
        report.add("INPUT_IO", "An input file could not be read.", error=True)
    except OverflowError:
        report = Report(args.command)
        report.add("INPUT_TOO_LARGE", "The test interface accepts at most 64 MiB.", error=True)
    print(json.dumps(report.to_dict(), ensure_ascii=True))
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())

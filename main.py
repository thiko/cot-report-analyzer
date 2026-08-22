#!/usr/bin/env python3
"""Build the COT report data set consumed by the static site."""

import argparse
import logging
import sys

from cot.config import Config
from cot.pipeline import run
from cot.reports import REPORTS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--config", default="config.ini", help="path to config.ini")
    parser.add_argument("-r", "--report", action="append", choices=sorted(REPORTS),
                        help="only build this report type (repeatable)")
    parser.add_argument("--term-structure", action="store_true",
                        help="also scrape CME settlements for term structure curves "
                             "(CME blocks automated access, so this usually fails)")
    parser.add_argument("--no-download", action="store_true",
                        help="export from the existing database without fetching data")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = Config.load(args.config)

    logging.basicConfig(
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        level=logging.DEBUG if args.verbose else getattr(logging, config.log_level, logging.INFO),
    )

    run(config,
        report_keys=args.report,
        with_term_structure=args.term_structure,
        download=not args.no_download)
    return 0


if __name__ == "__main__":
    sys.exit(main())

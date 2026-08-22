#!/usr/bin/env python3
"""Build the COT report data set consumed by the static site."""

import argparse
import logging
import sys

from cot.config import Config
from cot.pipeline import run, run_prices_only
from cot.reports import REPORTS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--config", default="config.ini", help="path to config.ini")
    parser.add_argument("-r", "--report", action="append", choices=sorted(REPORTS),
                        help="only build this report type (repeatable)")
    parser.add_argument("--term-structure", action="store_true",
                        help="also scrape CME settlements for term structure curves "
                             "(CME blocks automated access, so this usually fails)")
    parser.add_argument("--prices", action="store_true",
                        help="also refresh the price feed (off by default: the feed "
                             "answers shared address ranges with a standing HTTP 429)")
    parser.add_argument("--prices-only", action="store_true",
                        help="only refresh the price feed and rewrite prices.json, "
                             "leaving the COT data alone")
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

    if args.prices_only:
        run_prices_only(config)
        return 0

    run(config,
        report_keys=args.report,
        with_term_structure=args.term_structure,
        with_prices=args.prices,
        download=not args.no_download)
    return 0


if __name__ == "__main__":
    sys.exit(main())

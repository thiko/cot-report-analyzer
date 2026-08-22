"""Download and normalise the CFTC annual COT archives."""

import io
import logging
import re
import zipfile
from datetime import date
from pathlib import Path

import requests

from cot.reports import ReportSpec

logger = logging.getLogger(__name__)

BASE_URL = "https://www.cftc.gov/files/dea/history"
TIMEOUT = 120


def normalize_column(name: str) -> str:
    """Turn a CFTC header into a stable identifier.

    The archives are inconsistent: the legacy report uses spaces and
    parentheses, the others underscores, and several headers carry stray
    leading/trailing spaces or doubled underscores.
    """
    return re.sub(r"_+", "_", re.sub(r"[^0-9a-zA-Z]+", "_", name.strip())).strip("_")


def archive_url(spec: ReportSpec, year: int) -> str:
    return f"{BASE_URL}/{spec.archive_prefix}{year}.zip"


def fetch_year(spec: ReportSpec, year: int, cache_dir: Path) -> Path | None:
    """Return the extracted data file for one report year, downloading if needed.

    Past years never change, so a cached copy is reused. The current year is
    refreshed on every run because the CFTC appends to it weekly.
    """
    target = cache_dir / f"{spec.key}_{year}.txt"
    if target.exists() and year < date.today().year:
        logger.debug("Using cached %s", target.name)
        return target

    url = archive_url(spec, year)
    logger.info("Downloading %s", url)
    try:
        response = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        logger.warning("Download failed for %s: %s", url, exc)
        return target if target.exists() else None

    if response.status_code != 200:
        logger.warning("No archive for %s %s (HTTP %s)", spec.key, year, response.status_code)
        return target if target.exists() else None

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        member = _pick_member(archive, spec)
        if member is None:
            logger.warning("Archive for %s %s has no data file", spec.key, year)
            return None
        cache_dir.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(member))

    logger.info("Stored %s (%.1f MB)", target.name, target.stat().st_size / 1e6)
    return target


def _pick_member(archive: zipfile.ZipFile, spec: ReportSpec) -> str | None:
    names = archive.namelist()
    if spec.member in names:
        return spec.member
    # The archives have contained exactly one text file for two decades, but the
    # names have been renamed before; fall back to whatever is inside.
    candidates = [n for n in names if n.lower().endswith(".txt")]
    return candidates[0] if candidates else None

"""Runtime configuration, read from config.ini with CLI overrides.

Secrets are the exception: they come from the environment only. config.ini is
committed, so a key placed there would be published on the next data push. The
weekly workflow injects the key as a repository secret; locally a gitignored
.env file next to config.ini does the same job.
"""

import configparser
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Only the key is read from the environment, and only under this name. Keeping
# it to one fixed name means a misconfigured pipeline fails loudly at the fetch
# rather than falling back to some other variable that happens to be set.
API_KEY_ENV = "ALPHAVANTAGE_API_KEY"

DEFAULTS = {
    "cache_directory": "outputs/tmp",
    "data_directory": "data",
    "database_filename": "cot.db",
    "history_years": "5",
    "log_level": "INFO",
}


def load_dotenv(path: str | Path = ".env") -> None:
    """Read KEY=value lines into the environment, for local runs.

    A real environment variable always wins: in CI the secret is already set
    and a stale .env checked out by accident must not override it. Absent file
    is the normal case and not an error.
    """
    try:
        text = Path(path).read_text()
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        os.environ.setdefault(name.strip(), value.strip().strip("'\""))


@dataclass(frozen=True)
class Config:
    cache_dir: Path
    data_dir: Path
    database: Path
    history_years: int
    log_level: str
    api_key: str | None

    @classmethod
    def load(cls, path: str | Path = "config.ini") -> "Config":
        parser = configparser.ConfigParser()
        parser.read_dict({"app": DEFAULTS})
        parser.read(path)
        app = parser["app"]

        if app.get("alphavantage_api_key"):
            raise ValueError(
                f"config.ini carries an API key. It is committed, so the key would be "
                f"published on the next data push. Move it to ${API_KEY_ENV} and revoke "
                f"the one that was in the file.")

        load_dotenv(Path(path).parent / ".env")
        cache_dir = Path(app["cache_directory"])
        return cls(
            cache_dir=cache_dir,
            data_dir=Path(app["data_directory"]),
            database=cache_dir / app["database_filename"],
            history_years=app.getint("history_years"),
            log_level=app["log_level"].upper(),
            api_key=os.environ.get(API_KEY_ENV) or None,
        )

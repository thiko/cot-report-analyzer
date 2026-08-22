"""Runtime configuration, read from config.ini with CLI overrides."""

import configparser
from dataclasses import dataclass
from pathlib import Path

DEFAULTS = {
    "cache_directory": "outputs/tmp",
    "data_directory": "data",
    "database_filename": "cot.db",
    "history_years": "5",
    "log_level": "INFO",
}


@dataclass(frozen=True)
class Config:
    cache_dir: Path
    data_dir: Path
    database: Path
    history_years: int
    log_level: str

    @classmethod
    def load(cls, path: str | Path = "config.ini") -> "Config":
        parser = configparser.ConfigParser()
        parser.read_dict({"app": DEFAULTS})
        parser.read(path)
        app = parser["app"]

        cache_dir = Path(app["cache_directory"])
        return cls(
            cache_dir=cache_dir,
            data_dir=Path(app["data_directory"]),
            database=cache_dir / app["database_filename"],
            history_years=app.getint("history_years"),
            log_level=app["log_level"].upper(),
        )

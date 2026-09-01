from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


RUNS_DIR = Path("runs")


def create_run_id() -> str:
    return datetime.now(
        timezone.utc
    ).strftime("%Y%m%d%H%M%S%f")


def save_trace(
    run_id: str,
    trace: list[dict],
) -> Path:

    RUNS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = (
        RUNS_DIR / f"{run_id}.json"
    )

    file_path.write_text(
        json.dumps(
            trace,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return file_path


def load_trace(
    run_id: str,
) -> list[dict]:

    file_path = (
        RUNS_DIR / f"{run_id}.json"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Trace not found: {run_id}"
        )

    return json.loads(
        file_path.read_text(
            encoding="utf-8"
        )
    )
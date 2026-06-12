"""Mock connector — serves the local ServiceNow CSV exports as a stand-in
"live" feed. This is the default source and needs no network or credentials,
so the full integration architecture works offline today; swap in the real
ServiceNow connector later by setting its env vars.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from pathlib import Path

from app.connectors.base import ITSMConnector

csv.field_size_limit(10_000_000)

_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = _ROOT / "data"            # real internal data (git-ignored, local only)
SAMPLE_DIR = _ROOT / "sample_data"   # synthetic demo data (committed, safe to publish)

# dataset -> filename token (whitespace-delimited piece of "Jul12025 INC.csv").
DATASET_TOKEN = {"incidents": "INC", "problems": "PRB", "changes": "CR", "tasks": "TSK"}


class MockConnector(ITSMConnector):
    source_name = "demo data"

    def _find_csv(self, dataset: str) -> Path | None:
        token = DATASET_TOKEN.get(dataset)
        if not token:
            return None
        # Prefer real local data/; fall back to the committed sample_data/.
        for base in (DATA_DIR, SAMPLE_DIR):
            if not base.exists():
                continue
            for p in base.glob("*.csv"):
                if token in p.stem.replace("_", " ").split():
                    return p
        return None

    def is_configured(self) -> bool:
        return any(self._find_csv(d) for d in DATASET_TOKEN)

    def fetch(self, dataset: str) -> tuple[list[str], Iterable[list[str]]]:
        path = self._find_csv(dataset)
        if not path:
            return [], iter(())
        f = open(path, "r", encoding="utf-8-sig", errors="replace", newline="")
        reader = csv.reader(f)
        header = next(reader, [])

        def rows() -> Iterator[list[str]]:
            try:
                for row in reader:
                    yield row
            finally:
                f.close()

        return header, rows()

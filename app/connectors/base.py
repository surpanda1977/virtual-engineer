"""Connector interface shared by all ITSM data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

# The four logical datasets the diagnostics engine understands.
DATASETS = ("incidents", "problems", "changes", "tasks")


class ITSMConnector(ABC):
    """A source of ITSM records.

    `fetch` returns a (columns, rows) pair for a dataset — the same tabular shape
    whether the data comes from a CSV export or a live REST API, so the data
    layer can load it identically.
    """

    source_name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """True if this connector has everything it needs to serve data."""

    @abstractmethod
    def fetch(self, dataset: str) -> tuple[list[str], Iterable[list[str]]]:
        """Return (column_names, row_iterator) for one dataset in DATASETS."""

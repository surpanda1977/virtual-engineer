"""
Pluggable ITSM data connectors.

The data layer (app/datasources.py) reads through a connector rather than
reading files directly, so the *source* of incidents/problems/changes/tasks can
be swapped without touching the diagnostics engine or UI:

  - MockConnector       — local CSV exports as a stand-in "live" feed (default).
  - ServiceNowConnector — live ServiceNow REST Table API (activated by env vars).

Select the active source with the VE_ITSM_SOURCE env var ("mock" | "servicenow").
ServiceNow is only used when it is both selected and configured; otherwise we
fall back to the mock so the app always works offline.
"""

from __future__ import annotations

import os

from app.connectors.base import ITSMConnector
from app.connectors.mock import MockConnector
from app.connectors.servicenow import ServiceNowConnector


def get_connector() -> ITSMConnector:
    source = os.environ.get("VE_ITSM_SOURCE", "mock").strip().lower()
    if source == "servicenow":
        sn = ServiceNowConnector()
        if sn.is_configured():
            return sn
        # Selected but not configured — degrade gracefully to mock.
    return MockConnector()


def source_status() -> dict:
    """Describe the active source (for the UI / health checks)."""
    conn = get_connector()
    return {
        "active": conn.source_name,
        "servicenow_configured": ServiceNowConnector().is_configured(),
        "requested": os.environ.get("VE_ITSM_SOURCE", "mock"),
    }


__all__ = ["ITSMConnector", "MockConnector", "ServiceNowConnector", "get_connector", "source_status"]

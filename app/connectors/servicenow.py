"""
ServiceNow connector — live data via the ServiceNow REST Table API.

Fully implemented and ready to use; it activates only when configured via env:

    SERVICENOW_INSTANCE   e.g. "dev123456"  or  "https://acme.service-now.com"
    SERVICENOW_USER + SERVICENOW_PASSWORD   (basic auth)   — or —
    SERVICENOW_TOKEN                         (OAuth bearer token)
    VE_ITSM_SOURCE=servicenow                (to select it)

Uses display values so fields come back human-readable (e.g. "3 - Low",
"Laptop - Lenovo"), matching the CSV exports the rest of the app expects.
Standard library only — no extra dependency.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from collections.abc import Iterable, Iterator

from app.connectors.base import ITSMConnector

# dataset -> (ServiceNow table, fields to request — mirror the CSV columns).
TABLES: dict[str, tuple[str, list[str]]] = {
    "incidents": ("incident", [
        "number", "priority", "short_description", "assignment_group", "state", "category",
        "opened_at", "closed_at", "resolved_at", "cmdb_ci", "impact", "urgency", "severity",
        "subcategory", "incident_state", "close_code", "close_notes", "made_sla",
        "reopen_count", "reassignment_count", "major_incident_state", "sys_created_on"]),
    "problems": ("problem", [
        "number", "short_description", "state", "resolution_code", "assignment_group",
        "cmdb_ci", "related_incidents", "sys_created_on", "closed_at"]),
    "changes": ("change_request", [
        "number", "type", "approval", "backout_plan", "assignment_group", "impact",
        "expected_start", "cmdb_ci", "sys_created_on", "closed_at"]),
    "tasks": ("sc_task", [
        "number", "priority", "state", "short_description", "assignment_group",
        "cat_item", "request_item", "sys_created_on", "closed_at"]),
}

PAGE_SIZE = 1000
MAX_PAGES = 200  # safety cap (≤ 200k records / dataset)


class ServiceNowConnector(ITSMConnector):
    source_name = "ServiceNow (live)"

    def __init__(self) -> None:
        inst = os.environ.get("SERVICENOW_INSTANCE", "").strip()
        if inst and "://" not in inst:
            inst = f"https://{inst}.service-now.com"
        self.base_url = inst.rstrip("/")
        self.user = os.environ.get("SERVICENOW_USER", "").strip()
        self.password = os.environ.get("SERVICENOW_PASSWORD", "").strip()
        self.token = os.environ.get("SERVICENOW_TOKEN", "").strip()

    def is_configured(self) -> bool:
        return bool(self.base_url and (self.token or (self.user and self.password)))

    def _auth_header(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        creds = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        return {"Authorization": f"Basic {creds}"}

    def _get(self, table: str, fields: list[str], offset: int) -> list[dict]:
        params = urllib.parse.urlencode({
            "sysparm_limit": PAGE_SIZE,
            "sysparm_offset": offset,
            "sysparm_fields": ",".join(fields),
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
        })
        url = f"{self.base_url}/api/now/table/{table}?{params}"
        req = urllib.request.Request(url, headers={"Accept": "application/json", **self._auth_header()})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8")).get("result", [])

    def fetch(self, dataset: str) -> tuple[list[str], Iterable[list[str]]]:
        if dataset not in TABLES:
            return [], iter(())
        table, fields = TABLES[dataset]

        def rows() -> Iterator[list[str]]:
            for page in range(MAX_PAGES):
                records = self._get(table, fields, page * PAGE_SIZE)
                if not records:
                    return
                for rec in records:
                    yield [str(rec.get(f, "")) for f in fields]
                if len(records) < PAGE_SIZE:
                    return

        return list(fields), rows()

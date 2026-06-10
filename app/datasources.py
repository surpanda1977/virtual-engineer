"""
ITSM data layer.

Loads the four ServiceNow CSV exports (Incidents, Problems, Changes, Tasks)
into a local SQLite database and provides query helpers for cross-domain
correlation. The shared key across Incidents/Problems/Changes is `cmdb_ci`
(the affected configuration item), plus `assignment_group` and timestamps.

The database (data/itsm.db) is built lazily and rebuilt whenever a source CSV
is newer than the DB. Everything stays local — data/ is git-ignored.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from datetime import datetime
from pathlib import Path

csv.field_size_limit(10_000_000)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "itsm.db"

# Filename token (whitespace-delimited) -> table name.
SOURCES = {"INC": "incidents", "PRB": "problems", "CR": "changes", "TSK": "tasks"}

# Per-table: which raw column to normalise into which ISO datetime helper column.
DATE_COLUMNS = {
    "incidents": {"opened_at": "opened_iso", "resolved_at": "resolved_iso", "closed_at": "closed_iso"},
    "changes": {"sys_created_on": "created_iso", "expected_start": "start_iso", "closed_at": "closed_iso"},
    "problems": {"sys_created_on": "created_iso", "closed_at": "closed_iso"},
    "tasks": {"sys_created_on": "created_iso", "closed_at": "closed_iso"},
}

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
)


def parse_dt(value: str) -> datetime | None:
    v = (value or "").strip()
    if not v or v.upper() == "UNKNOWN":
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    return None


def _iso(value: str) -> str | None:
    dt = parse_dt(value)
    return dt.isoformat(sep=" ") if dt else None


def _sanitize(col: str) -> str:
    """Make a CSV header safe as a SQLite column name."""
    c = re.sub(r"[^0-9a-zA-Z]+", "_", col.strip()).strip("_").lower()
    return c or "col"


def _find_csv(token: str) -> Path | None:
    for p in DATA_DIR.glob("*.csv"):
        if token in p.stem.replace("_", " ").split():
            return p
    return None


# --- Building the database --------------------------------------------------

def _needs_rebuild() -> bool:
    if not DB_PATH.exists():
        return True
    db_mtime = DB_PATH.stat().st_mtime
    for token in SOURCES:
        p = _find_csv(token)
        if p and p.stat().st_mtime > db_mtime:
            return True
    return False


def _load_table(conn: sqlite3.Connection, table: str, header, rows, date_map: dict) -> int:
    """Load a dataset (columns + row iterator from a connector) into `table`."""
    header = list(header or [])
    if not header:
        return 0
    cols = [_sanitize(h) for h in header]
    # De-duplicate any colliding sanitized names.
    seen: dict[str, int] = {}
    for i, c in enumerate(cols):
        if c in seen:
            seen[c] += 1
            cols[i] = f"{c}_{seen[c]}"
        else:
            seen[c] = 0

    extra_cols = list(date_map.values())
    all_cols = cols + extra_cols

    conn.execute(f"DROP TABLE IF EXISTS {table}")
    col_defs = ", ".join(f'"{c}" TEXT' for c in all_cols)
    conn.execute(f"CREATE TABLE {table} ({col_defs})")

    placeholders = ", ".join("?" for _ in all_cols)
    insert_sql = f"INSERT INTO {table} VALUES ({placeholders})"
    col_index = {c: i for i, c in enumerate(cols)}

    batch, total = [], 0
    for row in rows:
        row = (list(row) + [""] * len(cols))[: len(cols)]  # pad/trim to width
        extras = []
        for raw_col, iso_col in date_map.items():
            idx = col_index.get(_sanitize(raw_col))
            extras.append(_iso(row[idx]) if idx is not None else None)
        batch.append(row + extras)
        if len(batch) >= 5000:
            conn.executemany(insert_sql, batch)
            total += len(batch)
            batch.clear()
    if batch:
        conn.executemany(insert_sql, batch)
        total += len(batch)
    return total


def _create_indexes(conn: sqlite3.Connection) -> None:
    idx = [
        ("incidents", "cmdb_ci"), ("incidents", "assignment_group"), ("incidents", "opened_iso"),
        ("incidents", "category"), ("incidents", "priority"),
        ("changes", "cmdb_ci"), ("changes", "created_iso"),
        ("problems", "cmdb_ci"),
    ]
    for table, col in idx:
        try:
            conn.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_{col} ON {table}("{col}")')
        except sqlite3.OperationalError:
            pass  # column may not exist in a given export


def _build_fts(conn: sqlite3.Connection) -> bool:
    """Full-text index over incident text for similar-incident search."""
    try:
        conn.execute("DROP TABLE IF EXISTS incident_fts")
        conn.execute(
            "CREATE VIRTUAL TABLE incident_fts USING fts5("
            "number, short_description, close_notes, content='incidents', content_rowid='rowid')"
        )
        conn.execute(
            "INSERT INTO incident_fts(rowid, number, short_description, close_notes) "
            "SELECT rowid, number, short_description, "
            "COALESCE(close_notes,'') FROM incidents"
        )
        return True
    except sqlite3.OperationalError:
        return False  # FTS5 not compiled in — callers fall back to LIKE


def build(force: bool = False) -> dict:
    """Build the SQLite DB from the active connector. Returns row counts per table."""
    from app.connectors import get_connector  # lazy import (avoids any import cycle)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not force and not _needs_rebuild():
        return stats()
    connector = get_connector()
    counts: dict = {}
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        for table in SOURCES.values():  # incidents, problems, changes, tasks
            header, rows = connector.fetch(table)
            counts[table] = _load_table(conn, table, header, rows, DATE_COLUMNS.get(table, {}))
        _create_indexes(conn)
        counts["fts"] = _build_fts(conn)
        counts["source"] = connector.source_name
        conn.commit()
    finally:
        conn.close()
    return counts


def data_source() -> dict:
    """Active data source description (for /api/itsm/source and stats)."""
    from app.connectors import source_status

    return source_status()


_ensured = False


def ensure_loaded() -> None:
    global _ensured
    if not _ensured or _needs_rebuild():
        build()
        _ensured = True


def get_connection() -> sqlite3.Connection:
    ensure_loaded()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# --- Query helpers ----------------------------------------------------------

def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def stats() -> dict:
    if not DB_PATH.exists():
        return {}
    conn = sqlite3.connect(DB_PATH)
    try:
        out = {}
        for table in SOURCES.values():
            try:
                out[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.OperationalError:
                out[table] = 0
        return out
    finally:
        conn.close()


def get_incident(number: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM incidents WHERE number = ?", (number.strip(),)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def correlate_ci(ci: str, limit: int = 50) -> dict:
    """All incidents / problems / changes touching a configuration item."""
    conn = get_connection()
    try:
        out: dict = {"cmdb_ci": ci}
        out["incidents"] = [dict(r) for r in conn.execute(
            "SELECT number, priority, short_description, category, assignment_group, "
            "opened_iso, closed_iso, close_code FROM incidents WHERE cmdb_ci = ? "
            "ORDER BY opened_iso DESC LIMIT ?", (ci, limit))]
        out["incident_count"] = conn.execute(
            "SELECT COUNT(*) FROM incidents WHERE cmdb_ci = ?", (ci,)).fetchone()[0]
        out["problems"] = [dict(r) for r in conn.execute(
            "SELECT number, short_description, state, resolution_code, related_incidents, "
            "created_iso FROM problems WHERE cmdb_ci = ? ORDER BY created_iso DESC LIMIT ?", (ci, limit))]
        out["changes"] = [dict(r) for r in conn.execute(
            "SELECT number, type, approval, impact, created_iso, start_iso, closed_iso "
            "FROM changes WHERE cmdb_ci = ? ORDER BY created_iso DESC LIMIT ?", (ci, limit))]
        out["change_count"] = conn.execute(
            "SELECT COUNT(*) FROM changes WHERE cmdb_ci = ?", (ci,)).fetchone()[0]
        return out
    finally:
        conn.close()


def hotspots(top: int = 10) -> dict:
    """Aggregate views for the dashboard."""
    conn = get_connection()
    try:
        out: dict = {}
        out["top_cis"] = [dict(r) for r in conn.execute(
            "SELECT cmdb_ci AS ci, COUNT(*) AS incidents FROM incidents "
            "WHERE cmdb_ci IS NOT NULL AND cmdb_ci != '' "
            "GROUP BY cmdb_ci ORDER BY incidents DESC LIMIT ?", (top,))]
        out["top_groups"] = [dict(r) for r in conn.execute(
            "SELECT assignment_group AS team, COUNT(*) AS incidents FROM incidents "
            "WHERE assignment_group IS NOT NULL AND assignment_group != '' "
            "GROUP BY assignment_group ORDER BY incidents DESC LIMIT ?", (top,))]
        out["top_categories"] = [dict(r) for r in conn.execute(
            "SELECT category, COUNT(*) AS incidents FROM incidents "
            "WHERE category != '' GROUP BY category ORDER BY incidents DESC LIMIT ?", (top,))]
        out["by_month"] = [dict(r) for r in conn.execute(
            "SELECT substr(opened_iso,1,7) AS month, COUNT(*) AS incidents FROM incidents "
            "WHERE opened_iso IS NOT NULL GROUP BY month ORDER BY month")]
        cols = _table_columns(conn, "incidents")
        if "made_sla" in cols:
            total = conn.execute("SELECT COUNT(*) FROM incidents WHERE made_sla IN ('true','false')").fetchone()[0]
            breached = conn.execute("SELECT COUNT(*) FROM incidents WHERE made_sla = 'false'").fetchone()[0]
            out["sla"] = {"total": total, "breached": breached,
                          "breach_pct": round(100 * breached / total, 1) if total else 0}
        if "reopen_count" in cols:
            out["reopened"] = conn.execute(
                "SELECT COUNT(*) FROM incidents WHERE reopen_count NOT IN ('', '0')").fetchone()[0]
        if "major_incident_state" in cols:
            out["major_incidents"] = conn.execute(
                "SELECT COUNT(*) FROM incidents WHERE major_incident_state NOT IN ('', 'No')").fetchone()[0]
        return out
    finally:
        conn.close()


def change_incident_correlation(window_hours: int = 72, top: int = 15) -> list[dict]:
    """Find changes followed by incidents on the same CI within `window_hours`.

    A strong signal for change-induced incidents.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT c.number AS change, c.type, c.cmdb_ci AS ci, c.created_iso AS change_time, "
            "       COUNT(i.number) AS incidents_after "
            "FROM changes c JOIN incidents i "
            "  ON i.cmdb_ci = c.cmdb_ci "
            " AND i.opened_iso IS NOT NULL AND c.created_iso IS NOT NULL "
            " AND i.opened_iso >= c.created_iso "
            " AND julianday(i.opened_iso) - julianday(c.created_iso) <= ?/24.0 "
            "WHERE c.cmdb_ci IS NOT NULL AND c.cmdb_ci != '' "
            "GROUP BY c.number HAVING incidents_after > 0 "
            "ORDER BY incidents_after DESC LIMIT ?", (window_hours, top)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def similar_incidents(text: str, k: int = 8) -> list[dict]:
    """Find past incidents most similar to `text` (FTS5, with LIKE fallback)."""
    conn = get_connection()
    try:
        has_fts = bool(conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='incident_fts'").fetchone())
        terms = re.findall(r"[A-Za-z0-9]{3,}", text.lower())
        if has_fts and terms:
            query = " OR ".join(terms[:20])
            try:
                rows = conn.execute(
                    "SELECT i.number, i.short_description, i.category, i.close_code, "
                    "       i.close_notes, i.cmdb_ci, i.assignment_group "
                    "FROM incident_fts f JOIN incidents i ON i.rowid = f.rowid "
                    "WHERE incident_fts MATCH ? ORDER BY bm25(incident_fts) LIMIT ?", (query, k)).fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except sqlite3.OperationalError:
                pass
        # Fallback: LIKE on the longest terms.
        like_terms = sorted(set(terms), key=len, reverse=True)[:3] or [text[:20]]
        clause = " OR ".join("short_description LIKE ?" for _ in like_terms)
        params = [f"%{t}%" for t in like_terms] + [k]
        rows = conn.execute(
            f"SELECT number, short_description, category, close_code, close_notes, "
            f"cmdb_ci, assignment_group FROM incidents WHERE {clause} LIMIT ?", params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

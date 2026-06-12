"""
Generate a synthetic, 100% fake ITSM demo dataset into ./sample_data/.

This ships in the public repo so anyone who clones it can run the full app with
realistic-looking data — WITHOUT exposing any real internal data. Deterministic
(seeded) so re-running produces the same files.

Run:  C:\\Users\\surpanda\\tools\\python312\\python.exe tools\\make_sample_data.py
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(__file__).resolve().parent.parent / "sample_data"
OUT.mkdir(parents=True, exist_ok=True)

START = datetime(2025, 7, 1)
DAYS = 183  # ~6 months

# Fictional CIs: (name, category, assignment_group, [recurring symptoms])
CIS = [
    ("Acme Payments API", "App Support", ["Payment timeout at checkout", "Payment gateway returns 500", "Transaction declined in error"]),
    ("Globex CRM", "App Support", ["CRM login failure", "CRM page very slow to load", "Cannot save customer record"]),
    ("VPN Gateway", "Network Ops", ["VPN disconnects intermittently", "Cannot connect to VPN", "VPN very slow after login"]),
    ("Mailflow Online", "Cloud Ops", ["Email not syncing", "Cannot send external email", "Mailbox quota exceeded"]),
    ("Orion Data Warehouse", "Database Team", ["Data not refreshed overnight", "ETL job failed", "Report shows stale data"]),
    ("Helios HR Portal", "App Support", ["Payslip not visible", "HR portal error on submit", "Leave request stuck"]),
    ("Nimbus File Storage", "Cloud Ops", ["File restore request", "Shared drive inaccessible", "File sync conflict"]),
    ("Titan Auth Service", "Identity & Access", ["MFA prompt not received", "Account locked out", "SSO redirect loop"]),
    ("Vertex Print Service", "Deskside Support", ["Printer offline", "Print job stuck in queue", "Cannot scan to email"]),
    ("Atlas Monitoring", "Infrastructure", ["Server high CPU alert", "Disk space low on host", "Service needs restart"]),
]
CATEGORIES = ["Software", "Hardware", "Network", "Access", "Email", "Database", "Support"]
SUBCATS = ["Error", "Performance", "Outage", "Request", "Configuration"]
PRIORITIES = (["4 - Low"] * 6) + (["3 - Moderate"] * 3) + (["2 - High"] * 2) + ["1 - Critical"]
CLOSE_CODES = ["Solved (Permanently)", "Solved (Work Around)", "Not Reproducible",
               "Closed/Resolved by Caller", "Known Error"]
CONTACT = ["Self-service", "Phone", "Email", "Chat", "Walk-in"]


def dt(day_offset: float) -> str:
    return (START + timedelta(days=day_offset)).strftime("%Y-%m-%d %H:%M:%S")


def write(name: str, header: list[str], rows: list[list]):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {name}: {len(rows)} rows")


# --- Incidents --------------------------------------------------------------
inc_rows = []
inc_n = 4000000
for i in range(420):
    ci, group, symptoms = random.choice(CIS)
    opened = random.uniform(0, DAYS)
    dur_h = round(random.uniform(0.5, 72), 1)
    resolved = opened + dur_h / 24
    pr = random.choice(PRIORITIES)
    sd = random.choice(symptoms)
    inc_n += random.randint(1, 7)
    inc_rows.append([
        f"INC{inc_n:07d}", sd, pr, random.choice(CATEGORIES), random.choice(SUBCATS), group, ci,
        random.choice(CONTACT), dt(opened), dt(resolved), dt(resolved),
        random.choice(CLOSE_CODES), f"Resolved: {sd.lower()} addressed by {group}.",
        "Closed", random.choice(["true", "true", "true", "false"]),
        random.choice(["0", "0", "0", "1"]),
        random.choice(["No", "No", "No", "No", "Yes"]),
        pr.split(" - ")[1] if " - " in pr else pr, pr, pr.split(" - ")[0], dt(opened),
    ])

# Inject a change-induced spike: a change on Acme Payments API, then a burst of incidents right after.
spike_day = 95.0
for j in range(14):
    inc_n += random.randint(1, 4)
    inc_rows.append([
        f"INC{inc_n:07d}", "Payment gateway returns 500", "2 - High", "Software", "Outage",
        "App Support", "Acme Payments API", "Phone",
        dt(spike_day + 0.05 * j + 0.1), dt(spike_day + 0.05 * j + 0.5), dt(spike_day + 0.05 * j + 0.5),
        "Solved (Work Around)", "Rolled back to previous release.", "Closed", "false", "1", "Yes",
        "High", "2 - High", "2", dt(spike_day + 0.05 * j),
    ])

write("sample_INC.csv",
      ["number", "short_description", "priority", "category", "subcategory", "assignment_group",
       "cmdb_ci", "contact_type", "opened_at", "resolved_at", "closed_at", "close_code", "close_notes",
       "incident_state", "made_sla", "reopen_count", "major_incident_state", "impact", "urgency",
       "severity", "sys_created_on"], inc_rows)

# --- Changes ----------------------------------------------------------------
chg_rows = []
chg_n = 9000
# The change that precedes the payments spike.
chg_rows.append([f"CHG{chg_n:07d}", "Normal", "Approved", "Roll back deployment from snapshot",
                 "App Support", "2 - Medium", dt(spike_day - 1), "Acme Payments API",
                 dt(spike_day - 2), dt(spike_day - 0.5)])
for i in range(60):
    chg_n += random.randint(1, 9)
    ci, group, _ = random.choice(CIS)
    created = random.uniform(0, DAYS)
    chg_rows.append([
        f"CHG{chg_n:07d}", random.choice(["Normal", "Standard", "Emergency"]),
        random.choice(["Approved", "Approved", "Requested", "Rejected"]),
        "Snapshot taken; rollback plan documented.", group,
        random.choice(["1 - High", "2 - Medium", "3 - Low"]), dt(created + 1), ci,
        dt(created), dt(created + random.uniform(1, 5)),
    ])
write("sample_CR.csv",
      ["number", "type", "approval", "backout_plan", "assignment_group", "impact",
       "expected_start", "cmdb_ci", "sys_created_on", "closed_at"], chg_rows)

# --- Problems ---------------------------------------------------------------
prb_rows = []
prb_n = 50000
for i, (ci, group, symptoms) in enumerate(CIS[:8]):
    prb_n += random.randint(1, 5)
    prb_rows.append([
        f"PRB{prb_n:07d}", f"Recurring: {symptoms[0].lower()}",
        random.choice(["Root Cause Analysis", "Fix in Progress", "Closed", "Assess"]),
        random.choice(["Fix Applied", "Workaround", "", "Permanent Fix"]),
        "Problem Management", ci, str(random.randint(2, 18)),
        dt(random.uniform(20, DAYS)), "",
    ])
write("sample_PRB.csv",
      ["number", "short_description", "state", "resolution_code", "assignment_group",
       "cmdb_ci", "related_incidents", "sys_created_on", "closed_at"], prb_rows)

# --- Tasks ------------------------------------------------------------------
tsk_rows = []
tsk_n = 70000
CAT_ITEMS = ["New Laptop Request", "Software Install", "Access Request", "VPN Account",
             "Mailbox Setup", "Server Decommission", "Password Reset"]
for i in range(140):
    tsk_n += random.randint(1, 6)
    created = random.uniform(0, DAYS)
    tsk_rows.append([
        f"SCTASK{tsk_n:07d}", random.choice(PRIORITIES),
        random.choice(["Open", "Work in Progress", "Closed Complete"]),
        random.choice(CAT_ITEMS), random.choice(["Service Desk", "Deskside Support", "Cloud Ops"]),
        random.choice(CAT_ITEMS), f"RITM{tsk_n - 100:07d}", dt(created),
        dt(created + random.uniform(1, 10)),
    ])
write("sample_TSK.csv",
      ["number", "priority", "state", "short_description", "assignment_group",
       "cat_item", "request_item", "sys_created_on", "closed_at"], tsk_rows)

print("Done — synthetic demo data written to", OUT)

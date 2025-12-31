#!/usr/bin/env python3
from __future__ import annotations
from typing import Dict, List


def detect_segment(lead: Dict[str, str]) -> List[str]:
    """
    Segment based ONLY on the `industries` column from imported_leads.

    We trust the vendor's Industries field and do not scan other columns.
    """
    industries = (lead.get("industries") or "").strip()

    if not industries:
        return ["unknown"]

    # Handle multiple industries in a single string
    if ";" in industries:
        parts = [s.strip() for s in industries.split(";") if s.strip()]
        return parts or ["unknown"]
    if "," in industries:
        parts = [s.strip() for s in industries.split(",") if s.strip()]
        return parts or ["unknown"]

    return [industries]


def detect_persona(lead: Dict[str, str]) -> str:
    """
    Persona classification using ONLY:
      - seniority
      - departments
      - job_title

    We do not look at any other keys.
    """
    seniority = (lead.get("seniority") or "").lower().strip()
    dept = (lead.get("departments") or "").lower().strip()
    title = (lead.get("job_title") or "").lower().strip()

    # 1) Seniority is the strongest signal if present
    if any(w in seniority for w in ["c-level", "executive", "c-suite"]):
        return "executive"
    if any(w in seniority for w in ["vp", "vice president", "director"]):
        return "executive"
    if "manager" in seniority:
        return "operations"

    # 2) Departments → ops vs technical
    if any(w in dept for w in ["operations", "ops"]):
        return "operations"
    if any(w in dept for w in ["engineering", "lab", "laboratory", "science", "research"]):
        return "technical"

    # 3) Fallback to job title if seniority/departments are empty or vague
    if any(w in title for w in ["chief", "vp", "vice president", "director", "head of", "cso", "cto", "coo", "ceo"]):
        return "executive"
    if any(w in title for w in ["manager", "operations", "supervisor", "coordinator", "lead"]):
        return "operations"
    if any(w in title for w in ["scientist", "engineer", "analyst", "technician", "specialist", "epidemiologist", "chemist"]):
        return "technical"

    return "general"


if __name__ == "__main__":
    # Quick sanity test against the actual DB schema
    import sqlite3
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent
    DB_PATH = BASE_DIR.parent / "ai-leads" / "copper_emails.db"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM imported_leads LIMIT 5;")
    rows = cur.fetchall()
    conn.close()

    for row in rows:
        lead = dict(row)
        segs = detect_segment(lead)
        persona = detect_persona(lead)
        print("--------------------------------------------------")
        print(f"{lead.get('first_name','')} {lead.get('last_name','')} | {lead.get('company','')}")
        print("industries:", lead.get("industries",""))
        print("Segments:", segs)
        print("job_title:", lead.get("job_title",""))
        print("seniority:", lead.get("seniority",""))
        print("departments:", lead.get("departments",""))
        print("Persona:", persona)

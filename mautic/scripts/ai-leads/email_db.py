#!/usr/bin/env python3
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "copper_emails.db"


EMAILS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_email TEXT UNIQUE,
    lead_name TEXT,
    lead_title TEXT,
    company_name TEXT,
    approval_status TEXT,
    approval_timestamp TEXT,
    lead_website TEXT,
    post_edit_email TEXT,
    prompt_version TEXT,
    editor_version TEXT,
    scoring_version TEXT,
    created_at TEXT,
    duplicate_status INTEGER DEFAULT 0,
    push_status INTEGER DEFAULT 0,
    email_sent_status INTEGER DEFAULT 0
);
"""


EMAIL_REPLIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS email_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_email TEXT,
    contact_id TEXT,
    subject TEXT,
    parsed_body TEXT,
    in_reply_to TEXT,
    message_id TEXT UNIQUE,
    fetched_at TEXT,
    metadata_json TEXT
);
"""

INBOX_EMAILS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS inbox_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT,
    recipient TEXT,
    subject TEXT,
    parsed_body TEXT,
    message_id TEXT UNIQUE,
    folder TEXT,
    fetched_at TEXT,
    metadata_json TEXT
);
"""

IMPORTED_LEADS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS imported_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_email TEXT UNIQUE,
    work_email TEXT,
    personal_email TEXT,
    first_name TEXT,
    last_name TEXT,
    job_title TEXT,
    company TEXT,
    work_email_status TEXT,
    work_email_quality TEXT,
    work_email_confidence TEXT,
    primary_work_email_source TEXT,
    work_email_service_provider TEXT,
    catch_all_status TEXT,
    person_address TEXT,
    country TEXT,
    seniority TEXT,
    departments TEXT,
    personal_linkedin TEXT,
    profile_summary TEXT,
    company_linkedin TEXT,
    industries TEXT,
    company_summary TEXT,
    company_keywords TEXT,
    website TEXT,
    num_employees TEXT,
    phone TEXT,
    company_address TEXT,
    company_city TEXT,
    company_state TEXT,
    company_country TEXT,
    company_phone TEXT,
    company_email TEXT,
    technologies TEXT,
    latest_funding TEXT,
    latest_funding_amount TEXT,
    last_raised_at TEXT,
    facebook TEXT,
    twitter TEXT,
    youtube TEXT,
    instagram TEXT,
    annual_revenue TEXT,
    created_at TEXT,
    updated_at TEXT
);
"""


def _ensure_tables(cur: sqlite3.Cursor) -> None:
    cur.execute(EMAILS_TABLE_SQL)
    cur.execute(EMAIL_REPLIES_TABLE_SQL)
    cur.execute(INBOX_EMAILS_TABLE_SQL)
    cur.execute(IMPORTED_LEADS_TABLE_SQL)
    # Ensure approval_timestamp exists for legacy DBs
    cur.execute("PRAGMA table_info(emails)")
    cols = [r[1] for r in cur.fetchall()]
    if "approval_timestamp" not in cols:
        cur.execute("ALTER TABLE emails ADD COLUMN approval_timestamp TEXT")
    # Ensure imported_leads schema matches; if legacy data_json exists, recreate table (drops old data)
    cur.execute("PRAGMA table_info(imported_leads)")
    imported_cols = [r[1] for r in cur.fetchall()]
    if "data_json" in imported_cols or "canonical_email" not in imported_cols:
        cur.execute("DROP TABLE IF EXISTS imported_leads")
        cur.execute(IMPORTED_LEADS_TABLE_SQL)


def save_email_record(
    lead_email,
    lead_name=None,
    lead_title=None,
    company_name=None,
    lead_website=None,
    post_edit_email=None,
    prompt_version=None,
    editor_version=None,
    scoring_version=None,
):
    """Insert or update the newest outbound email for this lead_email."""
    if not lead_email:
        raise ValueError("lead_email is required")

    created_at = datetime.utcnow().isoformat(timespec="seconds")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    _ensure_tables(cur)

    cur.execute(
        """
        INSERT INTO emails (
            lead_email,
            lead_name,
            lead_title,
            company_name,
            lead_website,
            post_edit_email,
            prompt_version,
            editor_version,
            scoring_version,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(lead_email) DO UPDATE SET
            lead_name       = excluded.lead_name,
            lead_title      = excluded.lead_title,
            company_name    = excluded.company_name,
            lead_website    = excluded.lead_website,
            post_edit_email = excluded.post_edit_email,
            prompt_version  = excluded.prompt_version,
            editor_version  = excluded.editor_version,
            scoring_version = excluded.scoring_version,
            created_at      = excluded.created_at
        ;
        """,
        (
            lead_email,
            lead_name,
            lead_title,
            company_name,
            lead_website,
            post_edit_email,
            prompt_version,
            editor_version,
            scoring_version,
            created_at,
        ),
    )

    conn.commit()
    conn.close()


def save_email_reply(
    contact_email: str,
    contact_id: str = None,
    subject: str = None,
    parsed_body: str = None,
    in_reply_to: str = None,
    message_id: str = None,
    metadata_json=None,
):
    """
    Store an inbound reply (idempotent on message_id).
    Only a parsed body/summary is stored (no raw MIME or HTML).
    """
    if not contact_email:
        raise ValueError("contact_email is required to save a reply")

    fetched_at = datetime.utcnow().isoformat(timespec="seconds")

    if metadata_json is None:
        metadata_text = None
    elif isinstance(metadata_json, str):
        metadata_text = metadata_json
    else:
        import json
        metadata_text = json.dumps(metadata_json)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    _ensure_tables(cur)

    cur.execute(
        """
        INSERT INTO email_replies (
            contact_email,
            contact_id,
            subject,
            parsed_body,
            in_reply_to,
            message_id,
            fetched_at,
            metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET
            contact_email = excluded.contact_email,
            contact_id    = excluded.contact_id,
            subject       = excluded.subject,
            parsed_body   = excluded.parsed_body,
            in_reply_to   = excluded.in_reply_to,
            fetched_at    = excluded.fetched_at,
            metadata_json = excluded.metadata_json
        ;
        """,
        (
            contact_email,
            contact_id,
            subject,
            parsed_body,
            in_reply_to,
            message_id,
            fetched_at,
            metadata_text,
        ),
    )

    conn.commit()
    conn.close()


def save_inbox_email(
    sender: str,
    recipient: str = None,
    subject: str = None,
    parsed_body: str = None,
    message_id: str = None,
    folder: str = None,
    metadata_json=None,
):
    """Store an inbound email (idempotent on message_id)."""
    fetched_at = datetime.utcnow().isoformat(timespec="seconds")

    if metadata_json is None:
        metadata_text = None
    elif isinstance(metadata_json, str):
        metadata_text = metadata_json
    else:
        import json
        metadata_text = json.dumps(metadata_json)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    _ensure_tables(cur)

    cur.execute(
        """
        INSERT INTO inbox_emails (
            sender,
            recipient,
            subject,
            parsed_body,
            message_id,
            folder,
            fetched_at,
            metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET
            sender       = excluded.sender,
            recipient    = excluded.recipient,
            subject      = excluded.subject,
            parsed_body  = excluded.parsed_body,
            folder       = excluded.folder,
            fetched_at   = excluded.fetched_at,
            metadata_json= excluded.metadata_json
        ;
        """,
        (
            sender,
            recipient,
            subject,
            parsed_body,
            message_id,
            folder,
            fetched_at,
            metadata_text,
        ),
    )

    conn.commit()
    conn.close()


def _normalize_import_row(row: dict) -> dict:
    """Map incoming CSV-style dict to DB columns."""
    # Strip helpers
    def g(key): return (row.get(key) or "").strip()

    work_email = g("Work Email")
    personal_email = g("Personal Email")
    canonical_email = work_email or personal_email

    return {
        "canonical_email": canonical_email,
        "work_email": work_email,
        "personal_email": personal_email,
        "first_name": g("First Name"),
        "last_name": g("Last Name"),
        "job_title": g("Job Title"),
        "company": g("Company"),
        "work_email_status": g("Work Email Status"),
        "work_email_quality": g("Work Email Quality"),
        "work_email_confidence": g("Work Email Confidence"),
        "primary_work_email_source": g("Primary Work Email Source"),
        "work_email_service_provider": g("Work Email Service Provider"),
        "catch_all_status": g("Catch-all Status"),
        "person_address": g("Person Address"),
        "country": g("Country"),
        "seniority": g("Seniority"),
        "departments": g("Departments"),
        "personal_linkedin": g("Personal LinkedIn"),
        "profile_summary": g("Profile Summary"),
        "company_linkedin": g("Company LinkedIn"),
        "industries": g("Industries"),
        "company_summary": g("Company Summary"),
        "company_keywords": g("Company Keywords"),
        "website": g("Website"),
        "num_employees": g("# Employees"),
        "phone": g("Phone"),
        "company_address": g("Company Address"),
        "company_city": g("Company City"),
        "company_state": g("Company State"),
        "company_country": g("Company Country"),
        "company_phone": g("Company Phone"),
        "company_email": g("Company Email"),
        "technologies": g("Technologies"),
        "latest_funding": g("Latest Funding"),
        "latest_funding_amount": g("Latest Funding Amount"),
        "last_raised_at": g("Last Raised At"),
        "facebook": g("Facebook"),
        "twitter": g("Twitter"),
        "youtube": g("Youtube"),
        "instagram": g("Instagram"),
        "annual_revenue": g("Annual Revenue"),
    }


def save_imported_leads(rows):
    """
    Upsert imported leads (list of dicts) into imported_leads table.
    Canonical_email is work_email or personal_email; duplicates merge on canonical_email.
    """
    if not rows:
        return
    now = datetime.utcnow().isoformat(timespec="seconds")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    _ensure_tables(cur)

    insert_sql = """
    INSERT INTO imported_leads (
        canonical_email, work_email, personal_email, first_name, last_name, job_title, company,
        work_email_status, work_email_quality, work_email_confidence, primary_work_email_source,
        work_email_service_provider, catch_all_status, person_address, country, seniority, departments,
        personal_linkedin, profile_summary, company_linkedin, industries, company_summary, company_keywords,
        website, num_employees, phone, company_address, company_city, company_state, company_country,
        company_phone, company_email, technologies, latest_funding, latest_funding_amount, last_raised_at,
        facebook, twitter, youtube, instagram, annual_revenue, created_at, updated_at
    ) VALUES (
        :canonical_email, :work_email, :personal_email, :first_name, :last_name, :job_title, :company,
        :work_email_status, :work_email_quality, :work_email_confidence, :primary_work_email_source,
        :work_email_service_provider, :catch_all_status, :person_address, :country, :seniority, :departments,
        :personal_linkedin, :profile_summary, :company_linkedin, :industries, :company_summary, :company_keywords,
        :website, :num_employees, :phone, :company_address, :company_city, :company_state, :company_country,
        :company_phone, :company_email, :technologies, :latest_funding, :latest_funding_amount, :last_raised_at,
        :facebook, :twitter, :youtube, :instagram, :annual_revenue, :created_at, :updated_at
    )
    ON CONFLICT(canonical_email) DO UPDATE SET
        work_email = excluded.work_email,
        personal_email = excluded.personal_email,
        first_name = excluded.first_name,
        last_name = excluded.last_name,
        job_title = excluded.job_title,
        company = excluded.company,
        work_email_status = excluded.work_email_status,
        work_email_quality = excluded.work_email_quality,
        work_email_confidence = excluded.work_email_confidence,
        primary_work_email_source = excluded.primary_work_email_source,
        work_email_service_provider = excluded.work_email_service_provider,
        catch_all_status = excluded.catch_all_status,
        person_address = excluded.person_address,
        country = excluded.country,
        seniority = excluded.seniority,
        departments = excluded.departments,
        personal_linkedin = excluded.personal_linkedin,
        profile_summary = excluded.profile_summary,
        company_linkedin = excluded.company_linkedin,
        industries = excluded.industries,
        company_summary = excluded.company_summary,
        company_keywords = excluded.company_keywords,
        website = excluded.website,
        num_employees = excluded.num_employees,
        phone = excluded.phone,
        company_address = excluded.company_address,
        company_city = excluded.company_city,
        company_state = excluded.company_state,
        company_country = excluded.company_country,
        company_phone = excluded.company_phone,
        company_email = excluded.company_email,
        technologies = excluded.technologies,
        latest_funding = excluded.latest_funding,
        latest_funding_amount = excluded.latest_funding_amount,
        last_raised_at = excluded.last_raised_at,
        facebook = excluded.facebook,
        twitter = excluded.twitter,
        youtube = excluded.youtube,
        instagram = excluded.instagram,
        annual_revenue = excluded.annual_revenue,
        updated_at = excluded.updated_at
    ;
    """

    payloads = []
    for row in rows:
        norm = _normalize_import_row(row)
        if not norm.get("canonical_email"):
            continue
        norm["created_at"] = now
        norm["updated_at"] = now
        payloads.append(norm)

    if payloads:
        cur.executemany(insert_sql, payloads)
        conn.commit()
    conn.close()


def get_imported_leads():
    """
    Return all imported leads as list of dicts.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    _ensure_tables(cur)
    cur.execute(
        """
        SELECT
            first_name, last_name, job_title, company, personal_email, work_email,
            work_email_status, work_email_quality, work_email_confidence, primary_work_email_source,
            work_email_service_provider, catch_all_status, person_address, country, seniority,
            departments, personal_linkedin, profile_summary, company_linkedin, industries,
            company_summary, company_keywords, website, num_employees, phone, company_address,
            company_city, company_state, company_country, company_phone, company_email,
            technologies, latest_funding, latest_funding_amount, last_raised_at, facebook,
            twitter, youtube, instagram, annual_revenue
        FROM imported_leads
        ORDER BY id ASC
        """
    )
    cols = [col[0] for col in cur.description]
    rows = []
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        # Map back to original CSV-like keys for downstream scripts
        rows.append({
            "First Name": d.get("first_name", ""),
            "Last Name": d.get("last_name", ""),
            "Job Title": d.get("job_title", ""),
            "Company": d.get("company", ""),
            "Personal Email": d.get("personal_email", ""),
            "Work Email": d.get("work_email", ""),
            "Work Email Status": d.get("work_email_status", ""),
            "Work Email Quality": d.get("work_email_quality", ""),
            "Work Email Confidence": d.get("work_email_confidence", ""),
            "Primary Work Email Source": d.get("primary_work_email_source", ""),
            "Work Email Service Provider": d.get("work_email_service_provider", ""),
            "Catch-all Status": d.get("catch_all_status", ""),
            "Person Address": d.get("person_address", ""),
            "Country": d.get("country", ""),
            "Seniority": d.get("seniority", ""),
            "Departments": d.get("departments", ""),
            "Personal LinkedIn": d.get("personal_linkedin", ""),
            "Profile Summary": d.get("profile_summary", ""),
            "Company LinkedIn": d.get("company_linkedin", ""),
            "Industries": d.get("industries", ""),
            "Company Summary": d.get("company_summary", ""),
            "Company Keywords": d.get("company_keywords", ""),
            "Website": d.get("website", ""),
            "# Employees": d.get("num_employees", ""),
            "Phone": d.get("phone", ""),
            "Company Address": d.get("company_address", ""),
            "Company City": d.get("company_city", ""),
            "Company State": d.get("company_state", ""),
            "Company Country": d.get("company_country", ""),
            "Company Phone": d.get("company_phone", ""),
            "Company Email": d.get("company_email", ""),
            "Technologies": d.get("technologies", ""),
            "Latest Funding": d.get("latest_funding", ""),
            "Latest Funding Amount": d.get("latest_funding_amount", ""),
            "Last Raised At": d.get("last_raised_at", ""),
            "Facebook": d.get("facebook", ""),
            "Twitter": d.get("twitter", ""),
            "Youtube": d.get("youtube", ""),
            "Instagram": d.get("instagram", ""),
            "Annual Revenue": d.get("annual_revenue", ""),
        })
    conn.close()
    return rows

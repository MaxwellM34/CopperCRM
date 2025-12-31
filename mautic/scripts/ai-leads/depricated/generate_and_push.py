#!/usr/bin/env python3
import csv
import os
import json
import base64
import urllib.request
import urllib.error
import urllib.parse
import re
import argparse

from dotenv import load_dotenv
from pathlib import Path

# ---------------------------------
# ENV + PROMPT VERSION SETUP
# ---------------------------------

# Force-load .env from the project root
load_dotenv("/srv/mautic/.env")

# Base directory for this script (e.g. /srv/mautic/scripts/ai-leads)
SCRIPT_DIR = Path(__file__).parent

# Folder where all system prompt text files live
# e.g. /srv/mautic/scripts/ai-leads/prompts/kraken_sdr_v1_system.txt
PROMPTS_DIR = SCRIPT_DIR / "prompts"

# Choose which prompt version to use.
# You can override this with env var PROMPT_ID, e.g. PROMPT_ID=kraken_sdr_v3
PROMPT_ID = os.environ.get("PROMPT_ID", "kraken_sdr_v2")

# Parse CLI arguments (e.g. --skip-ai)
parser = argparse.ArgumentParser()
parser.add_argument(
    "--skip-ai",
    action="store_true",
    help="Skip OpenAI email generation and just create/update contacts.",
)
args = parser.parse_args()

# ========= CONFIG =========

# CSV file path (inside the container /srv/mautic/scripts if you follow our volume setup)
CSV_PATH = os.environ.get("CSV_PATH", "leads.csv")

# Mautic connection (all from .env / docker-compose)
MAUTIC_BASE_URL = os.environ.get("MAUTIC_BASE_URL", "http://138.197.156.191/")
MAUTIC_USERNAME = os.environ.get("MAUTIC_USERNAME", "copper")
MAUTIC_PASSWORD = os.environ.get("MAUTIC_PASSWORD")

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # cheap + good

# Web scraping config (for "recent" company info)
ENABLE_COMPANY_WEB_LOOKUP = True
HTTP_TIMEOUT_SECONDS = 6
MAX_COMPANY_TEXT_LEN = 900   # keep this small to save tokens

# Simple cache so we only fetch each company once
COMPANY_WEB_CACHE = {}


# ========= WEB SCRAPING HELPERS =========

def normalize_website_url(url: str) -> str:
    """Clean and normalize a website URL to just the scheme + host."""
    if not url:
        return ""
    url = url.strip()
    if not url:
        return ""
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc:
        return ""
    cleaned = parsed._replace(path="", params="", query="", fragment="")
    return urllib.parse.urlunparse(cleaned)


def fetch_url(url: str, timeout: int = HTTP_TIMEOUT_SECONDS) -> str:
    """Fetch raw HTML from a URL, returning empty string on any error."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; KrakenSenseBot/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="ignore")
    except Exception:
        return ""


def strip_html(html: str) -> str:
    """Remove script/style tags and strip other HTML tags to plain text."""
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_company_recent_snippet(website: str, company_name: str) -> str:
    """Try to pull a short text snippet from the company's website/news pages."""
    base = normalize_website_url(website)
    if not base:
        return ""

    cache_key = base.lower()
    if cache_key in COMPANY_WEB_CACHE:
        return COMPANY_WEB_CACHE[cache_key]

    paths_to_try = ["", "/news", "/press", "/blog", "/media", "/insights"]
    best_text = ""

    for path in paths_to_try:
        url = base.rstrip("/") + path
        html = fetch_url(url)
        if not html:
            continue
        text = strip_html(html)
        if not text:
            continue
        # Prefer text that clearly mentions the company name
        if company_name and company_name.lower() in text.lower():
            best_text = text
            break
        # Fallback: first reasonably long text we see
        if len(text) > 300 and not best_text:
            best_text = text

    if best_text:
        best_text = best_text[:MAX_COMPANY_TEXT_LEN]

    COMPANY_WEB_CACHE[cache_key] = best_text
    return best_text


# ========= PROMPT HELPERS =========

def load_system_prompt(prompt_id: str) -> str:
    """
    Load the system prompt text from prompts/<prompt_id>_system.txt

    Example:
        prompt_id = "kraken_sdr_v1"
        file = prompts/kraken_sdr_v1_system.txt
    """
    path = PROMPTS_DIR / f"{prompt_id}_system.txt"
    if not path.exists():
        raise RuntimeError(f"System prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def get_system_prompt_filename(prompt_id: str) -> str:
    """Return just the filename of the system prompt for this version."""
    return f"{prompt_id}_system.txt"


# ========= OPENAI HELPER =========

def call_openai(prompt: str, prompt_id: str) -> str:
    """
    Call OpenAI chat completions using:
    - system prompt loaded from a versioned text file
    - user prompt built from the CSV row + scraped data
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    url = "https://api.openai.com/v1/chat/completions"

    # Load versioned system prompt from file
    system_content = load_system_prompt(prompt_id)

    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.6,
        "max_tokens": 260,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ],
    }

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenAI API HTTP error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenAI API connection error: {e}") from e

    try:
        content = resp_data["choices"][0]["message"]["content"].strip()
    except Exception:
        raise RuntimeError(f"Unexpected OpenAI response: {resp_data}")

    return content


# ========= MAUTIC HELPER =========

def mautic_create_or_update_contact(payload: dict) -> dict:
    """Send a contact create/update request to Mautic."""
    if not MAUTIC_PASSWORD:
        raise RuntimeError("MAUTIC_PASSWORD environment variable is not set.")

    url = f"{MAUTIC_BASE_URL.rstrip('/')}/api/contacts/new"

    auth_str = f"{MAUTIC_USERNAME}:{MAUTIC_PASSWORD}"
    auth_header = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    encoded = urllib.parse.urlencode(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_header}",
    }

    req = urllib.request.Request(url, data=encoded, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Mautic HTTP error {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Mautic connection error: {e}") from e


# ========= PROMPT BUILDER =========

def build_email_prompt(row: dict, recent_company_info: str = "") -> str:
    """
    Build the user-facing prompt that describes a single lead.
    This is passed as the 'user' message to OpenAI.
    """
    first = (row.get("First Name") or "").strip()
    last = (row.get("Last Name") or "").strip()
    full_name = (first + " " + last).strip() or "this person"

    job_title = (row.get("Job Title") or "").strip()
    company = (row.get("Company") or "").strip()
    country = (row.get("Country") or "").strip()
    seniority = (row.get("Seniority") or "").strip()
    departments = (row.get("Departments") or "").strip()
    industries = (row.get("Industries") or "").strip()
    company_summary = (row.get("Company Summary") or "").strip()
    profile_summary = (row.get("Profile Summary") or "").strip()
    website = (row.get("Website") or "").strip()

    # Keep summaries short to control token usage
    if company_summary:
        company_summary = company_summary[:700]
    if profile_summary:
        profile_summary = profile_summary[:700]
    if recent_company_info:
        recent_company_info = recent_company_info[:MAX_COMPANY_TEXT_LEN]

    parts = [
        f"Write a personalized cold email for {full_name}.",
        "",
        "Lead details:",
        f"- Name: {full_name}",
        f"- Role: {job_title}" if job_title else "",
        f"- Seniority: {seniority}" if seniority else "",
        f"- Department: {departments}" if departments else "",
        f"- Company: {company}" if company else "",
        f"- Country: {country}" if country else "",
        f"- Company website: {website}" if website else "",
        f"- Industries: {industries}" if industries else "",
        "",
        "Company summary (their company, from enrichment data):",
        company_summary if company_summary else "N/A",
        "",
        "Person profile summary (from LinkedIn-like source):",
        profile_summary if profile_summary else "N/A",
        "",
        "Recent info we could find online about their organisation (may be approximate):",
        recent_company_info if recent_company_info else "N/A",
        "",
        "Goal: Start a conversation about Kraken Sense rapid automated pathogen monitoring "
        "in water and wastewater, focusing on operational reliability, regulatory compliance, "
        "and public health protection.",
    ]

    return "\n".join([p for p in parts if p])


# ========= MAIN =========

def main():
    print(f"Using CSV: {CSV_PATH}")
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: CSV file '{CSV_PATH}' does not exist in this folder.")
        return

    if not MAUTIC_PASSWORD:
        print("ERROR: MAUTIC_PASSWORD environment variable is not set.")
        return

    # Only require OpenAI key if we are NOT skipping AI
    if not OPENAI_API_KEY and not args.skip_ai:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        print("Hint: You can use --skip-ai to run without generating emails.")
        return

    created = 0
    skipped = 0
    errors = 0

    # Default is comma separated. Change delimiter if your file is TSV.
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)  # delimiter="," by default

        print("Fieldnames from CSV:")
        print(reader.fieldnames)

        for idx, row in enumerate(reader, start=1):
            work_email = (row.get("Work Email") or "").strip()
            personal_email = (row.get("Personal Email") or "").strip()
            email = work_email or personal_email

            status = (row.get("Work Email Status") or "").strip().lower()

            # Debug to see what the script sees
            print(
                f"[{idx}] DEBUG work_email='{work_email}' "
                f"personal_email='{personal_email}' status='{status}'"
            )

            if not email:
                print(f"[{idx}] Skipping row – no email found in 'Work Email' or 'Personal Email'")
                skipped += 1
                continue

            first_name = (row.get("First Name") or "").strip()
            last_name = (row.get("Last Name") or "").strip()
            job_title = (row.get("Job Title") or "").strip()
            company = (row.get("Company") or "").strip()
            country = (row.get("Country") or "").strip()
            website = (row.get("Website") or "").strip()

            print(f"[{idx}] Processing {first_name} {last_name} <{email}> ...")

            try:
                recent_info = ""
                if ENABLE_COMPANY_WEB_LOOKUP and website:
                    recent_info = get_company_recent_snippet(website, company)

                # Build prompt regardless; may or may not call OpenAI
                prompt = build_email_prompt(row, recent_info)

                if args.skip_ai:
                    print(f"[{idx}] [SKIP AI] Not generating AI email for {email}.")
                    ai_email = ""
                else:
                    # Use the versioned system prompt specified by PROMPT_ID
                    ai_email = call_openai(prompt, PROMPT_ID).strip()
                    if len(ai_email) > 8000:
                        ai_email = ai_email[:8000]

                # Base payload for Mautic contact create/update
                payload = {
                    "email": email,
                    "firstname": first_name,
                    "lastname": last_name,
                    "company": company,
                    "position": job_title,
                    "country": country,
                    "website": website,
                    # Your original field for storing the AI-generated email
                    "first_personal_email": ai_email,
                    # Tag to indicate these contacts came from this AI import
                    "tags[]": "ai_import_wastewater",
                    # Track which prompt version was used
                    "prompt_version": PROMPT_ID,
                }

                # Store email into the matching custom field (same name as PROMPT_ID)
                # e.g. PROMPT_ID="kraken_sdr_v3" -> writes to Mautic field "kraken_sdr_v3"
                system_filename = get_system_prompt_filename(PROMPT_ID)
                payload[PROMPT_ID] = ai_email

                response = mautic_create_or_update_contact(payload)
                contact = response.get("contact") or {}
                cid = contact.get("id")

                print(f"[{idx}] ✔ Pushed to Mautic (id={cid}, email={email})")
                created += 1

            except Exception as e:
                print(f"[{idx}] ✖ ERROR for {email}: {e}")
                errors += 1

    print("\n===== SUMMARY =====")
    print(f"Created/updated contacts: {created}")
    print(f"Skipped (no email): {skipped}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()

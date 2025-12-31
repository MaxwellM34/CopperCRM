#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
load_dotenv() # load .env

# -----------------------
# PATHS
# -----------------------

BASE_DIR = Path(__file__).resolve().parent          # scripts/ai-leads
SCRIPTS_DIR = BASE_DIR.parent                       # scripts
ANALYZER_DIR = SCRIPTS_DIR / "analyzer"             # scripts/analyzer

if ANALYZER_DIR.exists() and str(ANALYZER_DIR) not in sys.path:
    sys.path.append(str(ANALYZER_DIR))

# -----------------------
# CONFIG - EDIT THESE
# -----------------------

# Get key from environment for safety
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # set this in your env/.env
OPENAI_MODEL = "gpt-4.1-mini"   # or gpt-5.1-mini

PROMPT_FILE = "prompts/first_email_prompt.txt"
OUTPUT_DIR = "generated"

# no CSV; data comes from DB importer
print("Prompt exists:", os.path.exists(PROMPT_FILE))


# -----------------------
# DEPENDENCIES
# -----------------------
from openai import OpenAI
from email_editor import edit_email, get_editor_version
from email_scoring import score_email, format_scoring_output, get_scoring_version
from email_db import save_email_record, get_imported_leads


client = OpenAI(api_key=OPENAI_API_KEY)


# -----------------------
# DATA LOADING
# -----------------------

def load_rows():
    return get_imported_leads()


def preview_rows(rows):
    print("\n=== CSV PREVIEW ===")
    print(f"Total rows: {len(rows)}\n")
    print("Idx | First Name | Last Name | Company | Work Email")
    print("-" * 60)
    for i, row in enumerate(rows, start=1):
        print(
            f"{i:>3} | {row.get('First Name','')} | "
            f"{row.get('Last Name','')} | "
            f"{row.get('Company','')} | {row.get('Work Email','')}"
        )
        if i >= 15:
            break
    print("-" * 60)
    print("Use these indexes in your selection.\n")


# -----------------------
# PARSE USER SELECTIONS
# -----------------------

def parse_selection(txt, total):
    txt = txt.lower().strip()
    if txt == "all":
        return list(range(1, total + 1))

    indices = set()
    parts = txt.split(",")

    for p in parts:
        p = p.strip()
        if not p:
            continue

        if "-" in p:
            start, end = p.split("-")
            try:
                start = int(start)
                end = int(end)
                for x in range(start, end + 1):
                    if 1 <= x <= total:
                        indices.add(x)
            except Exception:
                # ignore garbage
                pass
        else:
            try:
                x = int(p)
                if 1 <= x <= total:
                    indices.add(x)
            except Exception:
                # ignore garbage
                pass

    return sorted(indices)


# -----------------------
# PROMPT LOADING
# -----------------------

def load_prompt(path):
    if not os.path.exists(path):
        print(f"WARNING: Prompt file not found: {path}")
        return "Write a personalized cold email for this contact."

    return Path(path).read_text(encoding="utf-8")


def get_prompt_version() -> str:
    """
    Read the first line of PROMPT_FILE to get a version tag.
    Expected: '# VERSION: v00X'
    """
    try:
        text = Path(PROMPT_FILE).read_text(encoding="utf-8")
    except FileNotFoundError:
        return "unknown"

    lines = text.splitlines()
    if not lines:
        return "unknown"

    first = lines[0].strip()
    if first.startswith("# VERSION:"):
        return first.split(":", 1)[1].strip()

    return "unknown"


# -----------------------
# OUTPUT DIR HELPERS
# -----------------------

def get_prompt_output_dir():
    base = Path(PROMPT_FILE).stem  # e.g., "first_email_prompt"
    full_path = Path(OUTPUT_DIR) / base
    full_path.mkdir(parents=True, exist_ok=True)
    return full_path


def get_run_output_dir(prompt_dir: Path) -> Path:
    """
    Create a unique folder for this run under the prompt folder.
    Example: generated/first_email_prompt/run_20251202-180530
    """
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = prompt_dir / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nRun output folder: {run_dir}")
    return run_dir


def write_run_versions_file(
    run_dir: Path, prompt_version: str, editor_version: str, scoring_version: str
):
    """
    Create a txt file in the run folder that records
    which versions of the prompt, editor, and scoring rules were used.
    """
    content = [
        "RUN VERSION INFO",
        "----------------",
        f"Prompt file:        {PROMPT_FILE}",
        f"Prompt version:     {prompt_version}",
        "",
        "Editor rules file:  prompts/editor_rules.txt",
        f"Editor version:     {editor_version}",
        "",
        "Scoring rules file: prompts/scoring_rules.txt",
        f"Scoring version:    {scoring_version}",
        "",
        f"Generated at:       {datetime.now().isoformat(timespec='seconds')}",
    ]
    path = run_dir / "versions.txt"
    path.write_text("\n".join(content) + "\n", encoding="utf-8")
    print(f"Run versions file written to: {path}")


# -----------------------
# COST ESTIMATION
# -----------------------

def estimate_cost(input_tokens, output_tokens):
    """
    GPT-4.1-mini pricing:
      - Input:  $0.15 per 1M tokens
      - Output: $0.60 per 1M tokens
    """
    input_cost = input_tokens * (0.15 / 1_000_000)
    output_cost = output_tokens * (0.60 / 1_000_000)
    total_cost = input_cost + output_cost
    return input_cost, output_cost, total_cost


# -----------------------
# OPENAI GENERATION
# -----------------------

def generate_message(row, prompt_text):
    """
    Generate a message for this row.
    Returns: message_text, token_info_string, cost_info_string
    """

    row_json = json.dumps(row, indent=2, ensure_ascii=False)

    system_msg = (
        "You are Copper the Cat, the best cat in the world and beloved child of Maxwell McInnis, "
        "also working as an SDR email assistant helping Kraken Sense. "
        "Write high-quality message outputs in plain text."
    )

    user_msg = f"""
Here is the lead data as JSON Coppernelio:

{row_json}

Follow these instructions to generate the outreach message, good kitty:

{prompt_text}
"""

    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": system_msg,
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_msg,
                    }
                ],
            },
        ],
    )

    # Depending on SDK version, this may need to be adjusted, but leaving as-is
    message = resp.output_text

    # Token usage
    try:
        usage = resp.usage
        input_tokens = usage.input_tokens  # type: ignore
        output_tokens = usage.output_tokens  # type: ignore
        total_tokens = usage.total_tokens  # type: ignore

        token_info = (
            f"Input: {input_tokens} | Output: {output_tokens} | Total: {total_tokens}"
        )

        # Cost calculation
        in_cost, out_cost, total_cost = estimate_cost(input_tokens, output_tokens)
        cost_info = (
            f"Input cost: ${in_cost:.8f}, "
            f"Output cost: ${out_cost:.8f}, "
            f"Total cost: ${total_cost:.8f}"
        )

    except Exception:
        token_info = "Token usage not provided."
        cost_info = "Cost estimate unavailable."

    return message, token_info, cost_info


# -----------------------
# SAVE OUTPUT
# -----------------------

def make_safe_name(row):
    first = row.get("First Name", "").replace(" ", "_")
    last = row.get("Last Name", "").replace(" ", "_")
    email = row.get("Work Email", "") or row.get("Personal Email", "")
    email_prefix = email.split("@")[0] if email else ""

    base = "_".join([x for x in [first, last, email_prefix] if x]) or "lead"
    safe_name = "".join(c for c in base if c.isalnum() or c in "_-")
    return safe_name


def save_message(row, message: str, run_dir: Path, suffix: str) -> Path:
    """
    Save a message to the given run_dir with a suffix indicating pre/post edit.
    Example filename: First_Last_email__pre_edit.txt
    """
    safe_name = make_safe_name(row)
    filename = f"{safe_name}__{suffix}.txt"
    path = run_dir / filename
    path.write_text(message, encoding="utf-8")
    return path


# -----------------------
# TOKEN LOGGING
# -----------------------

def log_usage(info, prompt_dir: Path):
    usage_file = prompt_dir / "usage.txt"
    with usage_file.open("a", encoding="utf-8") as f:
        f.write(info + "\n")


# -----------------------
# MAIN LOGIC
# -----------------------

def main():
    rows = load_rows()
    if not rows:
        print("No imported leads in DB. Use the importer app to upload CSV.")
        return

    preview_rows(rows)

    choice = input("Which rows? (1, 1-5, 1,3,7, all): ")
    indices = parse_selection(choice, len(rows))

    if not indices:
        print("No valid selections. Exiting.")
        return

    prompt_text = load_prompt(PROMPT_FILE)
    prompt_dir = get_prompt_output_dir()
    run_dir = get_run_output_dir(prompt_dir)

    # Get versions for this run
    prompt_version = get_prompt_version()
    editor_version = get_editor_version()
    scoring_version = get_scoring_version()
    print(f"Using prompt version:  {prompt_version}")
    print(f"Using editor version:  {editor_version}")
    print(f"Using scoring version: {scoring_version}")

    # Write the versions.txt file
    write_run_versions_file(run_dir, prompt_version, editor_version, scoring_version)

    total_cost_accum = 0.0

    for idx in indices:
        row = rows[idx - 1]
        name = (row.get("First Name", "") + " " + row.get("Last Name", "")).strip()

        print(f"\n===== [{idx}] Generating message for {name} =====")

        try:
            # Generate from Copper the Cat
            original_message, token_info, cost_info = generate_message(row, prompt_text)

            # Run through the editor
            edited_message = edit_email(original_message)

            # Score the edited email (lead + email text)
            scores = score_email(row, edited_message)
            score_text = format_scoring_output(scores)

            # Save both pre- and post-edit versions and scoring report
            pre_path = save_message(row, original_message, run_dir, "pre_edit")
            post_path = save_message(row, edited_message, run_dir, "post_edit")
            score_path = save_message(row, score_text, run_dir, "score")

            # Derive lead fields from the CSV row for DB logging
            lead_email = row.get("Work Email") or row.get("Personal Email") or ""
            lead_name = name
            lead_title = row.get("Job Title") or row.get("Title") or ""
            company_name = row.get("Company") or row.get("Company Name") or ""
            lead_website = (
                row.get("Website")
                or row.get("Company Website")
                or row.get("Domain")
                or ""
            )

            if lead_email:
                try:
                    save_email_record(
                        lead_email=lead_email,
                        lead_name=lead_name,
                        lead_title=lead_title,
                        company_name=company_name,
                        lead_website=lead_website,
                        post_edit_email=edited_message,
                        prompt_version=prompt_version,
                        editor_version=editor_version,
                        scoring_version=scoring_version,
                    )
                    print(f"Saved latest email for {lead_email} to DB.")
                except Exception as db_err:
                    print(f"Warning: could not save to DB for {lead_email}: {db_err}")
            else:
                print("Warning: no email found in row; skipping DB save.")

            # Print final edited email
            print("\n=== FINAL EDITED EMAIL ===")
            print(edited_message)

            # Print scoring report
            print("\n=== SCORING REPORT ===")
            print(score_text)

            # Paths
            print(f"\nSaved pre-edit to:        {pre_path}")
            print(f"Saved post-edit to:       {post_path}")
            print(f"Saved scoring report to:  {score_path}")

            # Display usage
            print(f"\nToken usage:   {token_info}")
            print(f"Cost estimate: {cost_info}")

            # Update cost accumulator
            try:
                total_cost_accum += float(cost_info.split("Total cost: $")[1])
            except Exception:
                pass

            log_usage(f"[Row {idx}] {token_info} | {cost_info}", prompt_dir)

        except Exception as e:
            print(f"Error on row {idx}: {e}")

    print("\n=======================================")
    print(f"TOTAL ESTIMATED RUN COST: ${total_cost_accum:.8f}")
    if indices:
        print(f"COST PER EMAIL:           ${total_cost_accum/len(indices):.8f}")
    print("=======================================")

    log_usage(f"TOTAL RUN COST: ${total_cost_accum:.8f}", prompt_dir)

    print("\nDone!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime

# -----------------------
# PATHS / CONFIG
# -----------------------

BASE_DIR = Path(__file__).resolve().parent  # scripts/ai-leads
PROMPTS_DIR = BASE_DIR / "prompts"

MAIN_PROMPT = PROMPTS_DIR / "first_email_prompt.txt"

# Archive folder JUST for the email prompt
ARCHIVE_DIR = PROMPTS_DIR / "archive" / "first_email_prompt"

# File naming pattern: first_email_prompt_vNNN_YYYYMMDD-HHMM.txt
ARCHIVE_NAME_PREFIX = "first_email_prompt_v"


# -----------------------
# HELPERS
# -----------------------

def ensure_dirs():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def get_existing_versions():
    """
    Scan archive directory and return list of (version_int, Path).
    Example filename: first_email_prompt_v003_20251202-1758.txt
    """
    versions = []
    if not ARCHIVE_DIR.exists():
        return versions

    for p in ARCHIVE_DIR.glob(f"{ARCHIVE_NAME_PREFIX}*.txt"):
        name = p.stem  # e.g. first_email_prompt_v003_20251202-1758
        try:
            after_prefix = name.split(ARCHIVE_NAME_PREFIX, 1)[1]  # "003_2025..."
            ver_str = after_prefix.split("_", 1)[0]               # "003"
            ver_int = int(ver_str)
            versions.append((ver_int, p))
        except Exception:
            continue

    versions = sorted(versions, key=lambda x: x[0])
    if versions:
        print("[PROMPT DEBUG] Existing prompt versions:",
              [v for v, _ in versions])
    else:
        print("[PROMPT DEBUG] No existing prompt versions found.")
    return versions


def get_next_version():
    versions = get_existing_versions()
    if not versions:
        return 1
    return versions[-1][0] + 1


def read_main_prompt():
    if not MAIN_PROMPT.exists():
        raise FileNotFoundError(f"Main prompt not found: {MAIN_PROMPT}")
    return MAIN_PROMPT.read_text(encoding="utf-8")


def write_main_prompt_with_version(content: str, version: int):
    """
    Ensure main prompt has a VERSION header as first line.
    """
    lines = content.splitlines()
    header = f"# VERSION: v{version:03d}"

    if lines and lines[0].startswith("# VERSION:"):
        lines[0] = header
    else:
        lines.insert(0, header)

    MAIN_PROMPT.write_text("\n".join(lines) + "\n", encoding="utf-8")


# -----------------------
# CORE ARCHIVE LOGIC
# -----------------------

def archive_current_prompt():
    ensure_dirs()

    raw_content = read_main_prompt()

    next_ver = get_next_version()
    version_str = f"{next_ver:03d}"      # numeric string
    version_label = f"v{next_ver:03d}"   # human-readable label

    write_main_prompt_with_version(raw_content, next_ver)

    versioned_content = read_main_prompt()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    archive_name = f"{ARCHIVE_NAME_PREFIX}{version_str}_{timestamp}.txt"
    archive_path = ARCHIVE_DIR / archive_name

    archive_header = [
        f"# ARCHIVE VERSION: {version_label}",
        f"# ARCHIVED AT: {timestamp}",
        "",
    ]
    archive_text = "\n".join(archive_header) + versioned_content

    archive_path.write_text(archive_text, encoding="utf-8")

    print(f"[PROMPT] Archived current prompt to: {archive_path}")
    print(f"[PROMPT] Main prompt tagged as VERSION: {version_label}")


def main():
    if not MAIN_PROMPT.exists():
        print(f"[ERROR] Main prompt not found: {MAIN_PROMPT}")
        return

    archive_current_prompt()


if __name__ == "__main__":
    main()

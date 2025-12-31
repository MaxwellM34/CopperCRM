#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime

# -----------------------------
# PATHS & CONSTANTS
# -----------------------------

# scripts/ai-leads
BASE_DIR = Path(__file__).resolve().parent

# scripts/ai-leads/prompts
PROMPTS_DIR = BASE_DIR / "prompts"

# Main scoring rules file
MAIN_RULES = PROMPTS_DIR / "scoring_rules.txt"

# Where archived copies go:
# scripts/ai-leads/prompts/archive/scoring_rules/
ARCHIVE_DIR = PROMPTS_DIR / "archive" / "scoring_rules"

# File naming pattern:
#   scoring_rules_v001_YYYYMMDD-HHMM.txt
ARCHIVE_PREFIX = "scoring_rules_v"


# -----------------------------
# HELPERS
# -----------------------------

def ensure_dirs() -> None:
    """Make sure the archive directory exists."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def get_existing_versions():
    """
    Scan archive directory and return list of (version_int, Path).
    Example filename: scoring_rules_v003_20250224-1430.txt
    """
    versions = []
    if not ARCHIVE_DIR.exists():
        return versions

    for p in ARCHIVE_DIR.glob(f"{ARCHIVE_PREFIX}*.txt"):
        # e.g. name = 'scoring_rules_v003_20250224-1430'
        name = p.stem
        try:
            after_prefix = name.split(ARCHIVE_PREFIX, 1)[1]  # '003_20250224-1430'
            ver_str = after_prefix.split("_", 1)[0]          # '003'
            ver_int = int(ver_str)
            versions.append((ver_int, p))
        except Exception:
            continue

    return sorted(versions, key=lambda x: x[0])


def get_next_version() -> int:
    """Return the next integer version number (1, 2, 3, ...)."""
    versions = get_existing_versions()
    if not versions:
        return 1
    return versions[-1][0] + 1


def read_main_rules() -> str:
    """Read the current scoring_rules.txt content."""
    if not MAIN_RULES.exists():
        raise FileNotFoundError(f"Scoring rules not found: {MAIN_RULES}")
    return MAIN_RULES.read_text(encoding="utf-8")


def write_main_with_version(content: str, version: int) -> None:
    """
    Ensure scoring_rules.txt has a VERSION header as the first line.
    First line will be: '# VERSION: v001', '# VERSION: v002', etc.
    """
    lines = content.splitlines()
    header = f"# VERSION: v{version:03d}"

    if lines and lines[0].startswith("# VERSION:"):
        lines[0] = header
    else:
        lines.insert(0, header)

    MAIN_RULES.write_text("\n".join(lines) + "\n", encoding="utf-8")


# -----------------------------
# CORE ARCHIVE LOGIC
# -----------------------------

def archive_current_rules() -> None:
    ensure_dirs()

    raw_content = read_main_rules()

    # Decide new version number
    next_ver = get_next_version()          # 1, 2, 3, ...
    version_str = f"v{next_ver:03d}"       # 'v001', 'v002', ...

    # Update VERSION header in main rules file
    write_main_with_version(raw_content, next_ver)

    # Re-read so archive contains the versioned content
    versioned_content = read_main_rules()

    # Build archive file name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    # scoring_rules_v001_YYYYMMDD-HHMM.txt
    archive_name = f"{ARCHIVE_PREFIX}{next_ver:03d}_{timestamp}.txt"
    archive_path = ARCHIVE_DIR / archive_name

    # Add archive header at the top
    archive_header = [
        f"# ARCHIVE VERSION: {version_str}",
        f"# ARCHIVED AT: {timestamp}",
        "",
    ]
    archive_text = "\n".join(archive_header) + versioned_content

    archive_path.write_text(archive_text, encoding="utf-8")

    print(f"[scoring] Archived current rules to: {archive_path}")
    print(f"[scoring] Main scoring_rules.txt tagged as VERSION: {version_str}")


# -----------------------------
# ENTRY POINT
# -----------------------------

def main() -> None:
    if not MAIN_RULES.exists():
        print(f"[ERROR] scoring_rules.txt not found at: {MAIN_RULES}")
        return

    archive_current_rules()


if __name__ == "__main__":
    main()

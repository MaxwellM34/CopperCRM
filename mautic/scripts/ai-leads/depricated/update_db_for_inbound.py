#!/usr/bin/env python3
import sqlite3
from pathlib import Path

# Same location as email_db.py / ai_message_testing.py
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "copper_emails.db"


def column_names(cur, table_name: str) -> list[str]:
    cur.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cur.fetchall()]


def main():
    print(f"Using DB at: {DB_PATH}")

    if not DB_PATH.exists():
        print("WARNING: DB file does not exist at this path.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Show columns before
    try:
        before_cols = column_names(cur, "emails")
    except sqlite3.OperationalError as e:
        print(f"Error reading table 'emails': {e}")
        conn.close()
        return

    print("Columns BEFORE:", before_cols)

    # Add approval_status if missing
    if "approval_status" not in before_cols:
        print("Adding approval_status column...")
        cur.execute("ALTER TABLE emails ADD COLUMN  TEXT")

    # Add approval_timestamp if missing
    if "approval_timestamp" not in before_cols:
        print("Adding approval_timestamp column...")
        cur.execute("ALTER TABLE emails ADD COLUMN approval_timestamp TEXT")

    # 🔹 Add company_name if missing
    if "company_name" not in before_cols:
        print("Adding company_name column...")
        cur.execute("ALTER TABLE emails ADD COLUMN company_name TEXT")

    conn.commit()

    after_cols = column_names(cur, "emails")
    print("Columns AFTER:", after_cols)

    conn.close()
    print("DB updated for approval + company_name.")
    

if __name__ == "__main__":
    main()

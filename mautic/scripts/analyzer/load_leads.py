#!/usr/bin/env python3
import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "ai-leads" / "copper_emails.db"

def load_leads_df():
    """
    Loads ALL columns of imported_leads into a Pandas DataFrame.
    Forces all fields to strings.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM imported_leads", conn, dtype=str)
    conn.close()

    # ensure no NaN — normalize to empty strings
    df = df.fillna("")
    
    return df


def main():
    df = load_leads_df()
    print(df)
    print("\nTotal rows:", len(df))
    print("\nColumns loaded:", df.columns.tolist())


if __name__ == "__main__":
    main()

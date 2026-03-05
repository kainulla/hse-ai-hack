"""SQLite database setup, CSV loading, and query functions."""

import sqlite3
from pathlib import Path

import pandas as pd

from src.config import DATA_DIR, DB_PATH


def get_connection() -> sqlite3.Connection:
    """Get SQLite connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database and load CSVs."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY,
            date TEXT,
            type TEXT,
            type_label TEXT,
            severity INTEGER,
            org_id TEXT,
            org_name TEXT,
            location TEXT,
            description TEXT,
            causes TEXT,
            status TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS korgau_cards (
            id TEXT PRIMARY KEY,
            date TEXT,
            obs_type TEXT,
            obs_type_label TEXT,
            org_id TEXT,
            org_name TEXT,
            category TEXT,
            description TEXT,
            status TEXT
        )
    """)

    conn.commit()

    # Load CSVs if tables are empty
    count = cursor.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    if count == 0:
        incidents_path = DATA_DIR / "incidents.csv"
        if incidents_path.exists():
            df = pd.read_csv(incidents_path)
            df.to_sql("incidents", conn, if_exists="replace", index=False)
            print(f"Loaded {len(df)} incidents into DB")

    count = cursor.execute("SELECT COUNT(*) FROM korgau_cards").fetchone()[0]
    if count == 0:
        korgau_path = DATA_DIR / "korgau_cards.csv"
        if korgau_path.exists():
            df = pd.read_csv(korgau_path)
            df.to_sql("korgau_cards", conn, if_exists="replace", index=False)
            print(f"Loaded {len(df)} korgau cards into DB")

    conn.close()


def load_incidents(
    org_id: str | None = None,
    incident_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> pd.DataFrame:
    """Load incidents with optional filters."""
    conn = get_connection()
    query = "SELECT * FROM incidents WHERE 1=1"
    params = []

    if org_id:
        query += " AND org_id = ?"
        params.append(org_id)
    if incident_type:
        query += " AND type = ?"
        params.append(incident_type)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    query += " ORDER BY date"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def load_korgau(
    org_id: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> pd.DataFrame:
    """Load korgau cards with optional filters."""
    conn = get_connection()
    query = "SELECT * FROM korgau_cards WHERE 1=1"
    params = []

    if org_id:
        query += " AND org_id = ?"
        params.append(org_id)
    if category:
        query += " AND category = ?"
        params.append(category)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    query += " ORDER BY date"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_organizations() -> list[dict]:
    """Get list of organizations from DB."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT DISTINCT org_id, org_name FROM incidents ORDER BY org_id", conn
    )
    conn.close()
    return df.to_dict("records")

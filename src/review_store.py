"""Persistent, single-researcher annotations for patent records."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "reviews.sqlite3"
DECISIONS = ("Unreviewed", "Relevant", "Not relevant", "Needs follow-up")


def _connect(db_path):
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_reviews(db_path=DEFAULT_DB):
    """Create the review database on first use."""
    with _connect(db_path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                source TEXT NOT NULL,
                record_level TEXT NOT NULL,
                patent_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                rationale TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                watchlist INTEGER NOT NULL DEFAULT 0,
                next_action TEXT NOT NULL DEFAULT '',
                reviewed_at TEXT,
                PRIMARY KEY (source, record_level, patent_id)
            )
        """)


def load_reviews(db_path=DEFAULT_DB):
    """Return annotations keyed by (source, record level, patent ID)."""
    with _connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM reviews").fetchall()
    return {(row['source'], row['record_level'], row['patent_id']): dict(row) for row in rows}


def save_review(source, record_level, patent_id, decision, rationale='', tags='',
                watchlist=False, next_action='', db_path=DEFAULT_DB):
    """Upsert a review; keep an unreviewed record when it has watchlist notes."""
    if decision not in DECISIONS:
        raise ValueError(f"Unknown review decision: {decision}")
    if not source or not record_level or not patent_id:
        raise ValueError("Source, record level and patent ID are required")

    reviewed_at = datetime.now(timezone.utc).isoformat(timespec='seconds') if decision != 'Unreviewed' else None
    with _connect(db_path) as connection:
        connection.execute("""
            INSERT INTO reviews
                (source, record_level, patent_id, decision, rationale, tags,
                 watchlist, next_action, reviewed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, record_level, patent_id) DO UPDATE SET
                decision = excluded.decision,
                rationale = excluded.rationale,
                tags = excluded.tags,
                watchlist = excluded.watchlist,
                next_action = excluded.next_action,
                reviewed_at = excluded.reviewed_at
        """, (source, record_level, patent_id, decision, rationale.strip(), tags.strip(),
              int(watchlist), next_action.strip(), reviewed_at))

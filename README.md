# AI Safety Patent Dashboard

Streamlit dashboard for exploring AI safety patents.

## Setup
```bash
pip install -r requirements.txt
./run.sh
```

## Data
334 patents (2019–2025) from Google Patents, enriched with abstracts and IPC/CPC codes.

## Scoring
Patents are scored across 6 dimensions: AI relevance, safety relevance, machine reference, safety function, regulatory relevance, and BAuA fit — using both keyword matching and IPC code lookups.

## Research workflow

Use the **Review Queue** tab to work through unreviewed publications and patent families.
Select a record, inspect its abstract and source link, then save a researcher decision,
rationale, tags, and optionally a watchlist flag and next action. The queue shows progress
and can export reviewed records or the watchlist to CSV. Dashboard sidebar filters also
apply to the queue and its export.

Assessments persist between app restarts in `data/reviews.sqlite3` (created automatically
on first launch and ignored by git). Back up this file to retain your notes when moving
the dashboard to another machine. Automated relevance scores are independent of the
researcher's decisions.

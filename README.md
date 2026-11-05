# AI Safety Patent Dashboard

Streamlit dashboard for exploring AI safety patents.

## Setup
```bash
pip install -r requirements.txt
./run.sh
```

## Data
The dashboard loads the newest `data/patente_*.csv` Google Patents export and
`data/Anlage 1 - KI im Arbeitsschutz_Ergebnisse.xlsx` (the `Patentfamilie` sheet)
automatically. The current files contain 334 Google Patents publications and 135
Orbit/FAMPAT patent families. Use the **Source** or **Record Level** sidebar filters
to view either source, and the family analysis tab to explore legal status and markers.

Publications and families are different record levels and can overlap; combined counts
are not counts of unique inventions. For Orbit/FAMPAT records, the earliest family
publication date is used as a proxy for the filing date because the workbook does not
provide one. Filing-year charts and filters therefore use that proxy for these records.
The keyword-based relevance scores are primarily English-language heuristics and may
underestimate German-language workbook records; the workbook markers remain available
for filtering and expert review.

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

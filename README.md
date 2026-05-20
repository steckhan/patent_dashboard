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


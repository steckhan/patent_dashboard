# Patent Research Dashboard

**Purpose:** Interactive Streamlit dashboard for patent intelligence on AI components with safety functions in machinery, supporting BAuA research.

**Location:** `projects/patent-dashboard/`

## Structure

```
src/                  # Source code
  patent_recherche.py # Original scraper (reference)
data/                 # Existing output data + new data
docs/                 # Documentation, methodology notes
```

## Tech Stack
- **Dashboard:** Streamlit (Python)
- **Data pipeline:** Python (requests, pandas, BeautifulSoup)
- **Visualizations:** Plotly (interactive) replacing matplotlib
- **Language:** English UI
- **Runtime:** Local (Mac mini M1, 16GB)

## Agent Workflow

1. **Researcher** → audit scrapers, identify fixes, define dashboard requirements
2. **Developer** → build dashboard + fix data pipeline
3. **Redakteur** → documentation + UI text polish

## Data Sources (current)
- Google Patents (working — 94 patents returned)
- EPO Espacenet (broken — 0 results, selector issues)
- DPMA DEPATISnet (broken — 0 results, selector issues)
- WIPO PatentScope (broken — 0 results, selector issues)

## Search Scope
- Topic: AI/ML components with safety functions in machinery
- IPC classes: G06N+F16P, G06N+B25J, G06N+G05B, G06N+B60W
- Time range: 2019–present
- Queries: 5 English keyword combinations (see scraper config)

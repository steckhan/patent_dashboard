# Patent Intelligence Dashboard

An interactive Streamlit dashboard for analyzing patent trends and assignee landscapes in AI/ML components with safety functions in machinery. Designed for BAuA (Bundesanstalt für Arbeitsschutz und Arbeitsmedizin) researchers investigating the state of AI safety in industrial applications.

## Quick Start

```bash
cd projects/patent-dashboard
./run.sh
```

Then open your browser to **http://localhost:8501**

**Alternative (manual):**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run src/app.py
```

## Dashboard Views

The dashboard provides 8 main analysis tabs:

### 📈 Trend Dashboard
- Filing and grant timelines (year-over-year)
- Cumulative patent count over time
- Overview metrics (total patents, assignees, granted/pending counts)

### 🏢 Assignee Landscape
- Top 15 patent assignees by filing frequency
- Raw vs. normalized assignee name comparison
- Shows impact of name deduplication on company concentration

### 🌍 Jurisdiction Analysis
- Geographic distribution of filings across countries/regions (US, CN, JP, EP, DE, etc.)
- Patent counts and percentages by jurisdiction

### 🔎 Query Performance & Coverage
- Search query effectiveness (patents per query)
- Query overlap analysis showing redundancy ratios
- Identifies which queries produce unique results

### ⚖️ Regulation & BAuA
- Heuristic 0-3 scoring for AI relevance, occupational safety relevance, regulatory relevance, BAuA fit, market readiness and criticality
- Weighted Patent Priority Score using the BAuA-oriented weighting model
- Industrial AI Safety Relevance Index for work-safety watchlist triage
- Functional role note: assistance function, possible safety component, or unclear
- Top watchlist candidates and technology-field priority views

### 🏆 Competitive Intel
- Patent portfolio treemap by company and jurisdiction
- Innovation velocity by top assignees over time
- Grant-rate analysis by company

### 📝 Abstract Intelligence
- Keyword analysis from titles
- Search-query coverage matrix by assignee

### 📋 Patent Details
- Searchable, sortable table of all patents (94 records)
- Direct links to original patent pages
- Regulatory and BAuA scoring details per patent
- Text search across title and assignee name
- CSV export button (filtered data)

## Filters

All views respond to sidebar filters in real-time:
- **Filing date range** – slider control
- **Source** – multi-select (currently Google Patents; EPO/DPMA/WIPO coming)
- **Assignee** – multi-select (normalized names, e.g., "Nvidia Corporation")
- **Jurisdiction** – multi-select (country/region codes)
- **Search query** – filter by search terms used in scraping
- **BAuA priority** – filter by priority category
- **Technology field** – filter by derived technology tags
- **Patent Priority Score** – numeric score range slider
- **Functional role** – filter by assistance function, safety component or unclear

## Data Sources & Limitations

**Currently populated:**
- Google Patents: 94 patents (working)

**Broken/In progress:**
- EPO Espacenet: 0 results (403 Forbidden; requires institutional API access)
- DPMA DEPATISnet: 0 results (HTML selectors obsolete)
- WIPO PatentScope: 0 results (endpoint moved)

See `docs/researcher-audit.md` for technical fixes in progress.

**Data gaps:**
- **Abstracts:** Empty for all 94 records (Google Patents API limitation). Future enrichment will fetch from patent detail pages.
- **IPC codes:** Not extracted. Future work will classify patents by IPC category.
- **Coverage:** Only patents matching AI+safety keywords in machinery domain (2019–present).

## Project Structure

```
projects/patent-dashboard/
├── README.md                                 # This file
├── PROJECT.md                                # Project overview
├── requirements.txt                          # Python dependencies
├── run.sh                                    # Launcher script
│
├── src/
│   ├── app.py                               # Main Streamlit dashboard
│   ├── data_utils.py                        # Data loading & processing
│   └── patent_recherche.py                  # Original scraper (reference)
│
├── data/
│   ├── patente_20260309_1732_fixed.csv     # 94 patents (Google Patents)
│   └── assignee_mapping.csv                 # Name normalization lookup
│
└── docs/
    ├── ui-review.md                         # Dashboard UI polish suggestions
    ├── methodology.md                       # Data collection methodology
    └── researcher-audit.md                  # Scraper diagnosis & roadmap
```

## Data Processing

The dashboard automatically:
1. **Loads** the patent CSV via `data_utils.py`
2. **Enriches** with jurisdiction codes (extracted from patent ID prefix)
3. **Normalizes** assignee names (e.g., Nvidia variants → "Nvidia Corporation")
4. **Scores** patents for BAuA, EU AI Act and machinery-safety relevance using transparent title/abstract heuristics
5. **Caches** in memory for fast filtering and redraws

Normalization rules are stored in `data/assignee_mapping.csv`. This reduces 54 raw assignee names to consolidated groups, improving company-level analysis.

The regulatory scoring layer is a first-pass triage model. Because the current dataset lacks abstracts and IPC codes, scores are based mainly on titles and should be treated as a monitoring aid, not as a final legal or safety assessment.

## Future Roadmap

From the audit findings (`docs/researcher-audit.md`):

- [ ] **Phase 2a:** Fix scraper data sources (EPO OPS API, DPMA selectors, WIPO endpoint)
- [ ] **Phase 2b:** Enrich data with abstracts (fetch from patent URLs) and IPC codes
- [ ] **Phase 2c:** Calibrate regulatory scoring with abstracts, IPC codes and expert-reviewed examples
- [ ] **Phase 3:** Automated weekly scraper runs with email digests for researchers

## Technical Stack

- **Framework:** Streamlit (interactive web app, no DevOps)
- **Visualizations:** Plotly (interactive charts)
- **Data:** Pandas/NumPy
- **Language:** Python 3.14+

## Requirements

- Python 3.11+ (3.14 recommended)
- 16 MB disk space (data + venv)
- 500 MB RAM (typical usage)

All dependencies installed automatically by `run.sh`.

## Support & Issues

For questions about:
- **Dashboard:** Check `docs/ui-review.md` for known UI notes
- **Data:** See `docs/methodology.md` for collection methodology and caveats
- **Scrapers:** See `docs/researcher-audit.md` for technical status

---

**Last updated:** 2026-03-09  
**Data updated:** 2026-03-09  
**For:** BAuA Research Team

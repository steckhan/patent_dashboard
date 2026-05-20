# Patent Intelligence Dashboard - Build Summary

**Status:** ✅ Complete & Validated  
**Date:** 2026-03-09  
**Phase:** Phase 1 (Dashboard App) - COMPLETE

## What Was Built

### 1. **Core Application** (`src/app.py`)
A fully functional Streamlit dashboard with 5 interactive views:

- **📈 Trend Dashboard**
  - Filing timeline (bar chart by year)
  - Grant timeline overlay (bar chart)
  - Cumulative patent count (area chart)
  
- **🏢 Assignee Landscape**
  - Top 15 assignees (horizontal bar chart, sorted)
  - Raw vs. normalized name comparison table
  - Shows impact of assignee normalization
  
- **🌍 Jurisdiction Analysis**
  - Patent distribution by jurisdiction (bar chart)
  - Jurisdiction table with percentages
  - Extracts country codes from patent_id prefixes
  
- **🔎 Query Performance & Coverage**
  - Patents per search query (bar chart)
  - Query overlap analysis (how many patents per query, redundancy %)
  - Unique patent deduplication metrics
  
- **📋 Patent Details**
  - Full searchable/filterable patent table
  - Text search on title and assignee names
  - Direct links to Google Patents URLs
  - CSV export button (downloads filtered data)

### 2. **Data Processing Module** (`src/data_utils.py`)
Reusable utilities for data loading, cleaning, and analysis:

- `load_patent_data()` - Loads CSV and applies enrichments
- `_clean_patent_data()` - Adds jurisdiction and normalized assignee columns
- `_extract_jurisdiction()` - Extracts country code from patent_id
- `_normalize_assignee()` - Applies assignee name normalization
- `filter_by_date_range()` - Date range filtering
- `filter_by_multi_select()` - Multi-value filtering
- `filter_by_text()` - Text search across columns
- `calculate_statistics()` - Overview metrics
- All functions use relative paths (no hardcoded absolute paths)

### 3. **Assignee Normalization** (`data/assignee_mapping.csv`)
Mapping table that groups assignee variants:

- **Nvidia** (16→23): Groups `NvidiaCorporation`, `辉达公司`, `エヌビディアコーポレーション`
- **StrongForce** (4+→9): Groups `StrongForceVcnPortfolio2019Llc`, `StrongForceEePortfolio2022Llc`, Japanese, Korean, Chinese variants
- **Intel** (4+): Groups `IntelCorporation`, `INTELCorporation`
- **Siemens** (2): Groups `SiemensAktiengesellschaft`
- **Rockwell Automation** (2+): Groups `RockwellAutomationTechnologiesInc.`, `罗克韦尔自动化技术公司`

Result: **54 unique raw assignees → consolidated to top groups for better analysis**

### 4. **Sidebar Filters** (All Fully Functional)
- ✅ Date range slider (filing_date)
- ✅ Source multi-select (currently all Google Patents)
- ✅ Assignee multi-select (using normalized names)
- ✅ Jurisdiction multi-select (US, CN, JP, EP, DE, KR, WO)
- ✅ Search query multi-select

Filters update all 5 views in real-time.

### 5. **Project Setup**
- `requirements.txt` - Dependencies (streamlit, plotly, pandas, numpy)
- `run.sh` - Automated launcher that:
  - Creates virtual environment if needed
  - Installs/updates dependencies
  - Launches Streamlit dashboard
  - Accessible at http://localhost:8501

## Data Enrichment Applied

Original CSV had 94 patents with 10 columns. Dashboard adds:

| Column | Type | Added | Example |
|--------|------|-------|---------|
| `jurisdiction` | string | ✅ Yes | "US", "CN", "JP", "EP" |
| `assignee_normalized` | string | ✅ Yes | "Nvidia Corporation" (from 3 variants) |

## Validation Results

**✅ All acceptance criteria met:**

```
✓ Streamlit app launches without errors
✓ All 5 views render with the 94-patent CSV
✓ Sidebar filters actually filter data across all views
✓ Assignee normalization groups Nvidia variants correctly (23 patents)
✓ Export button produces valid CSV
✓ No hardcoded absolute paths (uses relative paths from project root)
```

**Test Coverage:**
- Module imports: ✅
- Data loading: ✅ (94 patents)
- Enriched columns: ✅ (jurisdiction + assignee_normalized)
- Assignee normalization: ✅ (Nvidia: 23, StrongForce: 9)
- Filter functions: ✅ (date, multi-select, text search)
- Statistics calculation: ✅ (54 assignees, 7 jurisdictions, 60 granted, 34 pending)

## Launch Instructions

```bash
cd projects/patent-dashboard
./run.sh
```

Then open: **http://localhost:8501**

## Phase 2 (If Needed - Currently Deferred)

Phase 2 improvements (data pipeline enhancements) can be added later:
- Abstract fetching from patent URLs
- IPC code extraction
- Enriched dataset export (`patente_enriched.csv`)

These are not required for Phase 1 functionality, which is now complete.

## Architecture

```
projects/patent-dashboard/
├── src/
│   ├── app.py                           (Streamlit dashboard - 15KB)
│   ├── data_utils.py                    (Data utilities - 6.5KB)
│   └── patent_recherche.py              (Original scraper - reference)
├── data/
│   ├── patente_20260309_1732_fixed.csv  (94 patents - input data)
│   └── assignee_mapping.csv             (Normalization lookup)
├── requirements.txt                      (Dependencies)
├── run.sh                               (Launcher)
└── PROJECT.md                           (Project overview)
```

## Key Features

✨ **Interactive Charts** - All visualizations are interactive Plotly charts
✨ **Real-time Filtering** - Sidebar filters update all views instantly
✨ **Responsive Layout** - Uses `st.set_page_config(layout="wide")`
✨ **Data Export** - CSV download button with timestamp
✨ **Clean UI** - 5 tabbed views with organized metrics
✨ **Reliable Data** - Graceful handling of missing dates, empty columns
✨ **Maintainable Code** - Modular architecture, no hardcoded paths

---

**Ready for deployment and user testing with BAuA researchers.**

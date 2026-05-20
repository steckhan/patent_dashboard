# Patent Data Collection & Analysis Methodology

**For:** BAuA Research Team  
**Updated:** 2026-03-09  
**Scope:** How patent data is collected, processed, and presented in the dashboard

---

## Data Collection

### Search Strategy

Patents are harvested from four international databases using **combined keyword + IPC class search**:

| Database | Status | Coverage | Notes |
|----------|--------|----------|-------|
| **Google Patents** | ✅ Working | US, CN, JP, EP, KR, DE, WO | 94 patents retrieved (2019–present) |
| **EPO Espacenet** | ⚠️ In progress | EU, international | Requires institutional API credentials |
| **DPMA DEPATISnet** | ⚠️ In progress | Germany, EU | HTML selectors require updating |
| **WIPO PatentScope** | ⚠️ In progress | International (PCT) | Endpoint deprecated; awaiting replacement |

### Search Scope

**Topic:** AI/ML components with safety functions in machinery  
**Keywords:** Artificial intelligence, machine learning, neural networks, safety controller, autonomous, intelligent system  
**IPC Classes:** G06N (computing methods), F16P (safety devices), B25J (industrial robots), G05B (process control), B60W (vehicle dynamics)  
**Time Range:** 2019–present  
**Volume:** ~5 keyword queries × 4 databases = 20 search combinations (currently: 5 queries × Google Patents only)

---

## Data Quality & Enrichment

### Current Dataset (94 Patents)

**Completeness by column:**
- Filing date: 100% (date when patent application was submitted)
- Grant date: 63.8% (60/94 patents granted; 34 pending examination)
- Title: 100% (official patent title)
- Assignee: 100% (company/organization holding patent)
- Source: 100% (all from Google Patents)
- **Abstracts: 0%** ← Critical gap (see below)
- **IPC codes: Missing** ← Not extracted (see below)

### Critical Data Gaps

#### 1. Missing Abstracts (0% filled)

**Problem:** The Google Patents API does not return abstract text—only metadata (title, assignee, filing date).

**Impact:** Prevents semantic analysis (e.g., clustering by safety domain, validating relevance to machinery safety).

**Fix (Phase 2):** Fetch abstracts by visiting each patent's public detail page and parsing HTML. ~8 minutes per monthly run (94 patents × 300ms/patent).

**Workaround (now):** Use patent titles as proxy for relevance. Titles are descriptive enough for filtering and high-level trends.

#### 2. IPC Codes Not Extracted

**Problem:** Patent applications list IPC (International Patent Classification) codes, but the scraper does not extract them.

**Impact:** Cannot filter by technology domain (e.g., show only "G06N" robotics patents).

**Fix (Phase 2):** Add post-processing step to parse IPC from patent title or via secondary API lookup.

---

### Assignee Normalization

**Why:** Companies file patents under variant names (English, Chinese, Japanese subsidiaries, different legal entities). Without normalization, the same company appears as multiple assignees, obscuring market concentration.

**Method:**
1. Extract unique raw assignee names from dataset (54 unique names)
2. Manually group variants by company (e.g., "NvidiaCorporation", "辉达公司", "エヌビディアコーポレーション" → all "Nvidia Corporation")
3. Store mapping in `data/assignee_mapping.csv` (lookup table)
4. Apply during data load (`data_utils.py` line 65–75)

**Example:**
```
Raw Name                      → Normalized Name            → Patent Count
NvidiaCorporation            → Nvidia Corporation         → 16 (Nvidia variants total: 23)
辉达公司 (Chinese)            → Nvidia Corporation         → 4
エヌビディアコーポレーション (Japanese) → Nvidia Corporation → 3
```

**Impact:** 
- Reveals true market concentration (Nvidia: ~24% of dataset instead of fragmented 16+4+3)
- Enables company-level trend analysis
- Improves top-assignee visualization

**Maintenance:** Lookup table is living document; add new variants as they appear in data.

---

## Derived Columns

The dashboard automatically adds enriched columns during data load:

### Jurisdiction
- **Method:** Extract country code from patent ID prefix (first 2 characters)
  - US5,... → US (United States)
  - CN114... → CN (China)
  - JP7... → JP (Japan)
  - EP3... → EP (European Patent Office)
  - etc.
- **Limitations:** Works for major jurisdictions; some patents may lack clear prefixes
- **Use:** Geographic distribution analysis (bar charts, tables)

### Assignee Normalized
- **Method:** Map raw name via `data/assignee_mapping.csv`
- **Default:** If name not in lookup, keep raw name as-is
- **Use:** Assignee landscape view, filtering, trend analysis

### BAuA and Regulatory Relevance Scoring

The dashboard now adds a first-pass triage layer for patents that may be strategically relevant for **BAuA, KI-Sicherheit, Industrial AI and Maschinensicherheit**.

**Scoring scale:** 0 to 3 for each dimension:

| Score | Meaning |
|-------|---------|
| 0 | Not relevant |
| 1 | Low or indirect relevance |
| 2 | Relevant signals |
| 3 | High strategic relevance |

**Dimensions:**

| Dimension | Purpose |
|-----------|---------|
| `ai_relevance_score` | Detects explicit or adaptive AI/ML, neural networks, computer vision and related methods |
| `safety_relevance_score` | Detects occupational safety, health, hazard, emergency, collision or protective-system relevance |
| `machine_reference_score` | Detects machinery, robotics, vehicles, production, equipment and industrial-work context |
| `safety_function_score` | Detects whether AI/control/recognition may be part of a protective or decision function |
| `regulatory_relevance_score` | Estimates possible EU AI Act, EU Machinery Regulation or product-safety relevance |
| `baua_fit_score` | Estimates connection to BAuA topics such as machine safety, AI evaluation, human-centered systems and risk assessment |
| `market_readiness_score` | Estimates concreteness, industrial implementation and assignee/product proximity |
| `criticality_score` | Estimates possible severity if the system fails |

**Functional role note:**  
Each patent also receives `functional_role` and `functional_role_comment`.

| Value | Interpretation |
|-------|----------------|
| `Assistenzfunktion` | Metadata suggests support, monitoring, guidance or operator assistance without a clear protective function |
| `Sicherheitsbauteil` | Metadata suggests a possible safety-relevant machine or protective function |
| `Unklar` | Metadata is insufficient or contains mixed assistance/protection signals |

This role label is deliberately conservative. It indicates whether a patent should be reviewed as a possible assistance function or safety component; it does not decide the legal classification under the EU Machinery Regulation.

**Weighted Patent Priority Score:**

| Dimension | Weight |
|-----------|--------|
| AI relevance | 20% |
| Safety / occupational-safety relevance | 25% |
| Regulatory relevance | 20% |
| BAuA fit | 20% |
| Market readiness | 10% |
| Criticality | 5% |

**Priority categories:**

| Score | Category |
|-------|----------|
| 0-1.0 | Observe, low priority |
| 1.1-2.0 | Relevant, check occasionally |
| 2.1-2.5 | High relevance |
| 2.6-3.0 | Strategic watchlist candidate |

**Industrial AI Safety Relevance Index:**  
This separate index emphasizes whether a patent is especially worth monitoring from an occupational-safety perspective. It combines AI as a safety-relevant component, proximity to machinery/work equipment, possible worker impact, regulatory relevance and BAuA fit.

**Important limitation:** Current scoring is title/abstract-based, but abstracts are still missing for the present CSV. The model therefore relies mainly on patent titles and should be interpreted as a transparent screening heuristic. Expert review and patent-record validation are required before using scores for regulatory, legal or policy conclusions.

---

## Known Limitations & Interpretation Notes

### Coverage Limitations

⚠️ **Google Patents only:** Current data excludes patents from EPO, DPMA, WIPO databases.
- Implication: Results are skewed toward US-filed patents and may miss European/Asian innovations.
- Fix: Expected Q2 2026 when other databases are restored.

⚠️ **Keyword bias:** Search results depend on how inventors describe their patents.
- Implication: Patents using different terminology (e.g., "adaptive control" vs. "artificial intelligence") may be missed.
- Mitigation: Multiple queries help, but gaps remain. Dashboard shows "query overlap" to highlight redundancy.

⚠️ **Time lag:** Patents appear with delays (1–2 years from filing to public record).
- Implication: Most recent (2025–2026) patent activity is underrepresented.
- Interpretation: Trend lines should be interpreted conservatively for most recent years.

### Assignee-Level Limitations

⚠️ **Normalization is manual:** Mapping is curated by hand, not algorithmic. New variants may appear and be missed until next update.
- Risk: A completely new spelling variant (e.g., typo in Google Patents) could appear as a separate assignee until identified.

⚠️ **Subsidiaries not distinguished:** Current normalization groups all Nvidia variants together, including subsidiaries and regional offices.
- Implication: Cannot separately analyze Nvidia's Japanese subsidiary vs. US headquarters.
- Mitigation: `data/assignee_mapping.csv` includes optional `country_code` column for future refinement.

### Temporal Limitations

⚠️ **Filing vs. grant lag:** Patents are filed first, then examined (2–5 year average). The 63.8% grant rate is misleading for recent filings.
- Interpretation: Pending patents from 2024–2025 are still under examination; don't interpret "pending" as "rejected."

---

## How to Interpret Dashboard Results

### Safe Interpretations ✅

- "**Nvidia is the top assignee in the current dataset**" — Supported by normalized data
- "**Filings increased from 2019 to 2023**" — Supported by trend line
- "**US patents dominate the dataset**" — Supported by jurisdiction breakdown (caveat: may be Google Patents bias)

### Unsafe Interpretations ❌

- "**EPO patents are non-existent**" — Actually, data source is incomplete
- "**Companies X, Y, Z don't patent**" — Possible they don't patent this specific domain, or we haven't found their patents yet
- "**The global AI safety patent market is 94 patents**" — We only scraped 4 databases, 5 queries; global market is much larger

---

## Data Refresh Schedule

**Current:** Manual, ad-hoc (last run: 2026-03-09)  
**Planned (Phase 3):** Automated weekly scraping with email digest for researchers

---

## For More Information

- **Scraper status & roadmap:** See `docs/researcher-audit.md`
- **Dashboard UI guide:** See `docs/ui-review.md`
- **Project overview:** See `PROJECT.md`

---

**Key Takeaway:**  
This dashboard provides a **reliable snapshot of Google Patents AI safety patent activity** (94 records, 2019–present). Interpret trends with caution; gaps in abstracts, IPC codes, and non-Google sources limit deeper analysis. For publication or policy work, validate findings against original patent records and supplementary databases.

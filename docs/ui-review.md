# Dashboard UI Review & Polish Suggestions

**Date:** 2026-03-09  
**Reviewer:** Redakteur  
**Scope:** Text clarity, consistency, and user guidance in `src/app.py`

---

## Summary

Overall, the UI text is **clean and functional**. No critical issues found. Below are minor polish suggestions to improve clarity and consistency for BAuA researchers.

---

## Suggested Edits

### 1. Sidebar Filter Headers – Add Brief Context

**Location:** Lines 97–110 (filter subheaders)

**Current:**
```python
st.sidebar.subheader("Filing Date Range")
st.sidebar.subheader("Source")
st.sidebar.subheader("Assignee")
st.sidebar.subheader("Jurisdiction")
st.sidebar.subheader("Search Query")
```

**Suggestion:**
Add a one-line hint text below each header for first-time users. Currently, labels are clear but users unfamiliar with the data might not know what "Source" includes:

```python
st.sidebar.subheader("Filing Date Range")
st.sidebar.caption("Narrow by when patents were filed")

st.sidebar.subheader("Source")
st.sidebar.caption("Filter by patent database (Google Patents, etc.)")

st.sidebar.subheader("Assignee")
st.sidebar.caption("Filter by normalized company names")

st.sidebar.subheader("Jurisdiction")
st.sidebar.caption("Filter by country/region code (US, CN, JP, etc.)")

st.sidebar.subheader("Search Query")
st.sidebar.caption("Filter by original search terms used")
```

**Rationale:** Researchers new to the data won't immediately know what each filter does. One-line hints improve discoverability without cluttering the UI.

---

### 2. Assignee Multi-Select – Clarify Why Normalized

**Location:** Line 113 (assignee multi-select label)

**Current:**
```python
"Select assignees (normalized)",
```

**Suggestion:**
Change to:
```python
"Select companies (normalized names)",
```

**Rationale:** 
- "Assignees" is patent terminology; "companies" is more intuitive for general researchers.
- Parenthetical "(normalized names)" clarifies that Nvidia variants are grouped together.
- Matches domain language used elsewhere in the dashboard (e.g., "Assignee Landscape" view title stays as-is for consistency with patent industry).

---

### 3. "Assignee Landscape" Tab – Add Subtitle

**Location:** Line 154 (view header)

**Current:**
```python
st.header("🏢 Assignee Landscape")
```

**Suggestion:**
```python
st.header("🏢 Assignee Landscape")
st.markdown("*Top organizations and the impact of name normalization*")
```

**Rationale:**
- Sets expectations that this view shows both raw and normalized names.
- Helps researchers understand that seeing "Nvidia Corporation" under multiple variants is intentional, not a bug.

---

### 4. "Query Performance & Coverage" Tab – Rename for Clarity

**Location:** Line 192 (view header)

**Current:**
```python
st.header("🔎 Query Performance & Coverage")
```

**Suggestion:**
```python
st.header("🔎 Query Performance & Coverage")
st.markdown("*Evaluate search effectiveness and identify gaps*")
```

**Rationale:**
- First-time users may not immediately understand what "query performance" means (search efficiency, redundancy ratio, or something else?).
- Subtitle clarifies this is about search quality and overlap, not system performance.

---

### 5. Detail Table Search Box – Better Placeholder

**Location:** Line 228 (text_input placeholder)

**Current:**
```python
search_text = st.text_input(
    "🔍 Search patents by title or assignee", 
    placeholder="e.g., 'Nvidia' or 'safety'"
)
```

**Suggestion:**
```python
search_text = st.text_input(
    "🔍 Search by title or company", 
    placeholder="e.g., 'Nvidia safety controller'"
)
```

**Rationale:**
- "Company" is clearer than "assignee" for researchers.
- Example placeholder is more realistic (researchers would search for multi-word terms like "safety controller", not just single words).

---

### 6. CSV Export Caption – Add Clarity on Filtering

**Location:** Line 267 (download_button)

**Current:**
```python
st.download_button(
    label="⬇️ Download as CSV",
    data=csv_data,
    ...
)
```

**Suggestion:**
```python
st.download_button(
    label="📥 Download as CSV",
    data=csv_data,
    ...
)
st.caption("*Downloads filtered data (respects all sidebar filters)*")
```

**Rationale:**
- Users may not realize that the export respects the active filters.
- Icon change (⬇️ to 📥) is purely optional—both work, but 📥 is more "export"-like.
- Caption clarifies that if you filter to US jurisdiction only, the CSV will only contain US patents.

---

### 7. Footer Text – Make More Specific

**Location:** Line 276–283 (footer markdown)

**Current:**
```python
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
        Patent Intelligence Dashboard | Data Source: Google Patents | BAuA Research
    </div>
    """,
    unsafe_allow_html=True
)
```

**Suggestion:**
```python
st.markdown(
    """
    <div style='text-align: center; color: #999; font-size: 0.85em;'>
        Patent Intelligence Dashboard | BAuA Research<br>
        Data: Google Patents | 94 patents (2019–present)<br>
        <a href='https://github.com/BAuA/patent-dashboard' style='color: #999; text-decoration: none;'>GitHub</a> | 
        <a href='./docs/methodology.md' style='color: #999; text-decoration: none;'>Methodology</a>
    </div>
    """,
    unsafe_allow_html=True
)
```

**Rationale:**
- Add data scope and date range for clarity ("2019–present").
- Add links to methodology docs and GitHub so researchers can dive deeper.
- Current footer is too bare; researchers will want to understand data provenance.

**Note:** Links may need adjustment based on actual paths/hosting; URLs shown are placeholders.

---

### 8. Metric Cards – Standardize Terminology

**Location:** Line 136–145 (render_overview_metrics)

**Current:**
```python
st.metric("Total Patents", stats['total_patents'])
st.metric("Unique Assignees", stats['unique_assignees'])
st.metric("Granted Patents", stats['patents_with_grants'])
st.metric("Pending Patents", stats['patents_pending'])
```

**Suggestion:**
Keep as-is, but add consistent subtitle labels:

```python
col1.metric("Total Patents", stats['total_patents'])
col1.caption("*All patents in dataset*")

col2.metric("Unique Assignees", stats['unique_assignees'])
col2.caption("*After name normalization*")

col3.metric("Granted", stats['patents_with_grants'])
col3.caption("*Patents with grant_date*")

col4.metric("Pending", stats['patents_pending'])
col4.caption("*Patents awaiting examination*")
```

**Rationale:**
- Metric labels are terse; one-line captions explain each metric without cluttering the visual.
- "Granted/Pending" (shorter) is more scannable than "Granted Patents/Pending Patents" in the context of 4 KPI cards.
- Clarifies that "Unique Assignees" counts normalized names, not raw names.

---

## No Issues Found

The following aspects of the UI are **already well done** and need no changes:

✅ **Page title & subtitle** ("Patent Intelligence Dashboard" + "Interactive analysis...") – clear and professional  
✅ **Tab names** (5 emoji-prefixed tabs) – immediately recognizable, consistent style  
✅ **Chart titles** ("Patents Filed by Year", "Top 15 Assignees", etc.) – descriptive and concise  
✅ **Axis labels** (x/y labels in Plotly charts) – all properly named  
✅ **Table column headers** – clear and consistent (patent_id, title, assignee_normalized, jurisdiction, etc.)  
✅ **Error handling** – graceful messages if data is empty  
✅ **Filter logic** – clear multi-select options with no confusing defaults  

---

## Implementation Priority

**High priority (improves clarity):**
1. Suggestion #2 – "Assignees" → "Companies" (one-word change, big impact)
2. Suggestion #6 – Add CSV filter clarification (one caption line)
3. Suggestion #1 – Add filter subheader hints (optional but recommended for UX)

**Medium priority (polish):**
4. Suggestions #3, #4 – Subtitles for Assignee and Query tabs
5. Suggestion #8 – Metric card captions

**Low priority (nice-to-have):**
6. Suggestion #5 – Placeholder example refinement
7. Suggestion #7 – Footer enhancement (requires GitHub/hosting setup confirmation)

---

## Testing Notes

All suggestions above are **non-breaking changes** and can be implemented incrementally:
- No data loading changes required
- No filter logic changes required
- Pure UI text additions/refinements

Recommend testing each change in a local Streamlit instance before committing to verify no visual regressions.

---

**Review complete.** Dashboard UI is solid; these are refinements, not repairs.

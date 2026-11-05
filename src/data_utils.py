"""
Data loading, cleaning, and normalization utilities for the patent dashboard.
"""

import os
import html
import warnings
import re
import pandas as pd
from pathlib import Path

# Suppress FutureWarnings about chained assignment (we're using copy() first)
warnings.filterwarnings('ignore', category=FutureWarning, message='.*ChainedAssignment.*')


TECHNOLOGY_FIELD_KEYWORDS = {
    'Industrial AI': [
        'industrial', 'production', 'manufacturing', 'factory', 'process optimization',
        'quality control', 'intelligent system', 'autonomous machine'
    ],
    'Robotik': [
        'robot', 'robotic', 'cobot', 'collaborative robot', 'manipulator', 'robot fleet',
        'drone'
    ],
    'Maschinensicherheit': [
        'safety controller', 'safety function', 'emergency stop', 'protective',
        'safety monitoring', 'risk reduction', 'machine safety', 'hazard',
        'safety assurance', 'safety control', 'hazard prevention', 'autonomous machine',
        'vehicle'
    ],
    'Computer Vision': [
        'computer vision', 'object recognition', 'instance segmentation',
        'person recognition', 'image recognition', 'visual', 'camera', 'vision'
    ],
    'Sensorik': [
        'sensor', 'sensor fusion', 'lidar', 'radar', 'camera', 'force sensor',
        'wearable', 'perception'
    ],
    'Human-Machine Interaction': [
        'human machine', 'human-machine', 'human feedback', 'operator',
        'interface', 'assistance', 'assistive', 'trust'
    ],
    'Predictive Maintenance': [
        'predictive maintenance', 'condition monitoring', 'fault prediction',
        'digital twin', 'diagnostic'
    ],
    'Algorithmic Management': [
        'task assignment', 'fleet management', 'work allocation', 'performance monitoring',
        'algorithmic management', 'scheduling'
    ],
}

AI_TERMS = [
    'artificial intelligence', 'machine learning', 'deep learning', 'neural network',
    'neural networks', 'computer vision', 'ai ', ' ai', 'ml ', ' ml', 'model',
    'classification', 'object recognition', 'instance segmentation', 'sensor fusion'
]

ADAPTIVE_AI_TERMS = [
    'autonomous', 'adaptive', 'learning', 'decision', 'control', 'safety function',
    'emergency', 'protective', 'real-time', 'perception'
]

SAFETY_TERMS = [
    'safety', 'emergency', 'protective', 'risk', 'hazard', 'collision', 'injury',
    'danger', 'monitoring', 'health', 'ergonomic', 'exposure'
]

MACHINE_TERMS = [
    'machine', 'machinery', 'robot', 'vehicle', 'industrial', 'factory', 'production',
    'manufacturing', 'equipment', 'workplace', 'work cell', 'fleet', 'autonomous machine'
]

SAFETY_FUNCTION_TERMS = [
    'safety function', 'safety controller', 'emergency stop', 'shutdown', 'protective',
    'person recognition', 'object recognition', 'collision', 'protective field',
    'monitoring', 'detection'
]

SAFETY_COMPONENT_TERMS = [
    'safety controller', 'safety function', 'emergency stop', 'shutdown',
    'protective', 'protective field', 'safety assurance', 'safety control',
    'hazard prevention', 'detecting hazards', 'detecting hazard', 'hazard detection',
    'collision', 'person recognition'
]

ASSISTANCE_FUNCTION_TERMS = [
    'assistance', 'assistive', 'human feedback', 'operator', 'interface',
    'remote monitoring', 'tracking', 'recommendation', 'guidance', 'support',
    'fleet management', 'task assignment'
]

MARKET_NEAR_TERMS = [
    'system', 'apparatus', 'device', 'platform', 'controller', 'chipset', 'fleet',
    'industrial', 'vehicle', 'robot', 'machine'
]

MAJOR_INDUSTRIAL_ASSIGNEES = [
    'nvidia', 'siemens', 'bosch', 'fanuc', 'abb', 'kuka', 'yaskawa', 'omron',
    'rockwell', 'mitsubishi', 'honeywell', 'schneider', 'caterpillar', 'toyota'
]

# ── IPC / CPC code lookup tables ────────────────────────────────────────────
# Each entry maps a technology field to a list of IPC/CPC prefixes.
# A code "matches" if it starts with any listed prefix.

IPC_TECHNOLOGY_MAP = {
    'Industrial AI':             ['G06N', 'G06Q'],
    'Robotik':                   ['B25J'],
    'Maschinensicherheit':       ['F16P', 'G05P', 'B60R'],
    'Computer Vision':           ['G06V', 'G06T'],
    'Sensorik':                  ['G01S', 'G01D', 'G01N'],
    'Human-Machine Interaction': ['G06F3', 'G08B'],
    'Predictive Maintenance':    ['G07C', 'G01M'],
    'Algorithmic Management':    ['G06Q10', 'G06Q50'],
}

# AI/ML presence signals
IPC_AI_PREFIXES = ['G06N', 'G06Q']

# Safety-relevant hardware / control
IPC_SAFETY_PREFIXES = ['F16P', 'G05B', 'G05D', 'B60R']

# Physical machine / robot context
IPC_MACHINE_PREFIXES = ['B25J', 'B62D', 'B60W', 'G05B', 'G05D', 'B66C', 'A01B']

# Safety-function-specific codes (autonomous stops, protective devices)
IPC_SAFETY_FUNCTION_PREFIXES = ['F16P3', 'G05B9', 'B25J9']

# Sets used for regulatory cross-check: AI ∩ machine/safety = strong regulatory signal
IPC_REGULATORY_AI      = {'G06N', 'G06Q'}
IPC_REGULATORY_MACHINE = {'F16P', 'B25J', 'G05B', 'G05D', 'B60W', 'B62D'}


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


def load_patent_data(csv_path=None):
    """
    Load patent data from available sources and perform basic cleaning.
    
    Args:
        csv_path: Path to CSV file. If None, uses default data location.
    
    Returns:
        DataFrame with cleaned patent data
    """
    if csv_path is not None:
        df = load_google_patents_data(csv_path)
    else:
        frames = []
        google_df = load_google_patents_data()
        if not google_df.empty:
            frames.append(google_df)

        orbit_df = load_orbit_fampat_data()
        if not orbit_df.empty:
            frames.append(orbit_df)

        df = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()

    if df.empty:
        return df

    # Clean up the data
    df = _clean_patent_data(df)

    return df


def load_google_patents_data(csv_path=None):
    """Load the newest Google Patents CSV and normalize source metadata."""
    if csv_path is None:
        data_dir = get_project_root() / "data"
        candidates = sorted(data_dir.glob("patente_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        fixed = data_dir / "patente_20260309_1732_fixed.csv"
        csv_path = candidates[0] if candidates else fixed

    if not Path(csv_path).exists():
        return pd.DataFrame()

    df = pd.read_csv(csv_path, encoding='utf-8', dtype={'abstract': str})
    df['source'] = df.get('source', 'Google Patents').fillna('Google Patents')
    df['record_level'] = 'Patent Publication'
    if 'publication_date' not in df.columns:
        df['publication_date'] = pd.NaT
    return df


def load_orbit_fampat_data(xlsx_path=None):
    """Load Orbit/FAMPAT patent-family workbook and map it to dashboard columns."""
    if xlsx_path is None:
        xlsx_path = get_project_root() / "data" / "Anlage 1 - KI im Arbeitsschutz_Ergebnisse.xlsx"

    xlsx_path = Path(xlsx_path)
    if not xlsx_path.exists():
        return pd.DataFrame()

    raw = pd.read_excel(xlsx_path, sheet_name='Patentfamilie', header=2, engine='openpyxl')
    raw = raw.dropna(subset=['Number']).copy()

    urls = _extract_orbit_hyperlinks(xlsx_path, row_offset=4, column='C')
    raw['_orbit_url'] = pd.Series(raw.index.map(urls), index=raw.index).fillna(
        raw['Link Patent family/ fulltext']
    )

    marker_map = {
        'Person': 'marker_person',
        'Roboter': 'marker_robot',
        'Maschinelles Lernen / Bildauswertung': 'marker_ml_vision',
        'Stop': 'marker_stop',
        'Schutz / Sicherheit': 'marker_safety',
        'KI': 'marker_ai',
        'Gefahr': 'marker_hazard',
        'Industriemaschine': 'marker_industrial_machine',
        'Kamera': 'marker_camera',
    }

    df = pd.DataFrame(index=raw.index)
    df['source'] = 'Orbit/FAMPAT'
    df['record_level'] = 'Patent Family'
    df['patent_id'] = raw['Number'].astype(str).str.strip()
    df['title'] = raw['Title'].apply(_strip_patent_prefix)
    df['assignee'] = raw['Applicant'].fillna('').astype(str).str.replace('\n', '; ', regex=False).str.strip()
    df['inventor'] = ''
    df['publication_date'] = raw['Publ.-\nDate'].apply(_earliest_multiline_date)
    df['filing_date'] = df['publication_date']
    df['grant_date'] = pd.NaT
    df['abstract'] = raw['Abstract'].apply(_strip_patent_prefix)
    df['url'] = raw['_orbit_url']
    df['query'] = 'KI im Arbeitsschutz'
    df['ipc_codes'] = ''
    df['family_members'] = raw['Doc.numbers\n(closely) family'].fillna('').astype(str).str.strip()
    df['family_member_count'] = df['family_members'].apply(lambda value: len([item for item in str(value).split('\n') if item.strip()]))
    df['family_publication_types'] = raw['Type'].fillna('').astype(str).str.strip()
    df['family_publication_dates'] = raw['Publ.-\nDate'].fillna('').astype(str).str.strip()
    df['family_legal_status'] = raw['Family legal status'].fillna('').astype(str).str.strip()
    df['family_legal_state'] = raw['Family legal state'].fillna('').astype(str).str.strip()
    df['legal_status_detail'] = raw['Legal status (Pending, Granted, Revoked, Expired, Lapsed)'].fillna('').astype(str).str.strip()
    df['legal_state_detail'] = raw['Legal state (Alive, Dead)'].fillna('').astype(str).str.strip()
    df['source_comments'] = raw['Comments'].fillna('').astype(str).str.strip()

    for source_col, target_col in marker_map.items():
        df[target_col] = raw[source_col].fillna(0).astype(str).str.strip().isin(['1', '1.0', 'x', 'X'])

    df['is_granted'] = df['family_legal_status'].eq('GRANTED')
    return df


def _extract_orbit_hyperlinks(xlsx_path, row_offset=4, column='C'):
    """Extract Orbit/FAMPAT hyperlinks from the family link column."""
    try:
        from openpyxl import load_workbook
    except ImportError:
        return []

    workbook = load_workbook(xlsx_path, read_only=False, data_only=True)
    worksheet = workbook['Patentfamilie']
    urls = {}
    for row in range(row_offset, worksheet.max_row + 1):
        cell = worksheet[f'{column}{row}']
        if cell.hyperlink and cell.hyperlink.target:
            urls[row - row_offset] = cell.hyperlink.target
        else:
            urls[row - row_offset] = cell.value or ''
    workbook.close()
    return urls


def _strip_patent_prefix(value):
    """Remove leading patent-number marker from Orbit title/abstract cells."""
    if pd.isna(value):
        return ''
    text = str(value).strip()
    return re.sub(r'^\([^)]{2,30}\)\s*', '', text).strip()


def _earliest_multiline_date(value):
    if pd.isna(value):
        return pd.NaT
    parts = [part.strip() for part in str(value).split('\n') if part.strip()]
    dates = pd.to_datetime(parts, errors='coerce')
    dates = dates[~pd.isna(dates)]
    return dates.min() if len(dates) else pd.NaT


def _clean_patent_data(df):
    """
    Internal function to clean patent data.
    
    Args:
        df: Raw patent DataFrame
    
    Returns:
        Cleaned DataFrame
    """
    df = df.copy()
    
    # Convert date columns to datetime
    for date_col in ['filing_date', 'publication_date', 'grant_date']:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    
    # Handle empty/null values in abstract
    if 'abstract' in df.columns:
        df['abstract'] = df['abstract'].fillna('').astype(str)
    
    # Decode HTML entities in title
    if 'title' in df.columns:
        df['title'] = df['title'].apply(lambda x: html.unescape(x) if isinstance(x, str) else x)
    
    # Extract jurisdiction from patent_id prefix
    df['jurisdiction'] = df['patent_id'].apply(_extract_jurisdiction)
    
    # Load assignee mapping once (vectorized)
    assignee_mapping = load_assignee_mapping()
    df['assignee_normalized'] = df['assignee'].map(assignee_mapping).fillna(df['assignee'])
    
    # Compute derived columns
    # 1. year_filed: extract year from filing_date
    df['year_filed'] = df['filing_date'].dt.year.astype('Int64')  # Use Int64 to allow NaN
    
    # 2. is_granted: boolean indicating if patent/family was granted
    if 'family_legal_status' in df.columns:
        family_granted = df['family_legal_status'].astype(str).str.upper().eq('GRANTED')
        df['is_granted'] = df['grant_date'].notna() | family_granted
    else:
        df['is_granted'] = df['grant_date'].notna()
    
    # 3. grant_lag_days: days between filing and grant (NaN if not granted)
    df['grant_lag_days'] = (df['grant_date'] - df['filing_date']).dt.days.astype('Int64')
    
    # 4. assignee_country: infer from jurisdiction
    df['assignee_country'] = df['jurisdiction'].apply(_infer_assignee_country)

    # 5. BAuA-oriented regulatory and safety relevance scoring
    df = enrich_regulatory_scores(df)
    
    return df


def enrich_regulatory_scores(df):
    """
    Add heuristic BAuA, EU AI Act, and machinery-safety relevance fields.

    Scoring uses title + abstract text (keyword matching) combined with
    IPC/CPC classification codes where available.  Scores provide a
    transparent first-pass triage layer, not a substitute for expert review.
    """
    enriched = df.copy()
    score_rows = enriched.apply(_score_patent_relevance, axis=1, result_type='expand')
    return pd.concat([enriched, score_rows], axis=1)


def _score_patent_relevance(row):
    """Score one patent on the 0-3 BAuA relevance scale."""
    text = _combined_patent_text(row)
    ipc_set = _extract_ipc_set(row)
    assignee = str(row.get('assignee_normalized', row.get('assignee', ''))).lower()
    is_granted = bool(row.get('is_granted', False))

    technology_fields = _detect_technology_fields(text, ipc_set)
    ai_score = _score_ai_relevance(text, ipc_set)
    safety_score = _score_safety_relevance(text, ipc_set)
    machine_score = _score_machine_reference(text, ipc_set)
    safety_function_score = _score_safety_function(text, ai_score, ipc_set)
    regulatory_score = _score_regulatory_relevance(ai_score, safety_score, machine_score, safety_function_score, ipc_set)
    baua_score = _score_baua_fit(ai_score, safety_score, regulatory_score, machine_score, text)
    market_score = _score_market_readiness(text, assignee, is_granted)
    criticality_score = _score_criticality(text, machine_score, safety_function_score)

    weighted_priority_score = round(
        (
            ai_score * 0.20
            + safety_score * 0.25
            + regulatory_score * 0.20
            + baua_score * 0.20
            + market_score * 0.10
            + criticality_score * 0.05
        ),
        2,
    )
    compact_average_score = round(
        (
            ai_score
            + safety_score
            + machine_score
            + safety_function_score
            + regulatory_score
            + baua_score
            + market_score
        )
        / 7,
        2,
    )
    safety_index_score = round(
        (
            safety_function_score * 0.25
            + machine_score * 0.20
            + safety_score * 0.20
            + regulatory_score * 0.20
            + baua_score * 0.15
        ),
        2,
    )

    return {
        'technology_fields': ', '.join(technology_fields),
        'ai_relevance_score': ai_score,
        'safety_relevance_score': safety_score,
        'machine_reference_score': machine_score,
        'safety_function_score': safety_function_score,
        'regulatory_relevance_score': regulatory_score,
        'baua_fit_score': baua_score,
        'market_readiness_score': market_score,
        'criticality_score': criticality_score,
        'patent_priority_score': weighted_priority_score,
        'compact_average_score': compact_average_score,
        'industrial_ai_safety_index': safety_index_score,
        'priority_category': _priority_category(weighted_priority_score),
        'safety_index_category': _safety_index_category(safety_index_score),
        'ai_act_relation': _relation_label(regulatory_score),
        'machinery_regulation_relation': _relation_label(max(regulatory_score, machine_score if safety_score >= 2 else 0)),
        'baua_action_field': _baua_action_field(baua_score, machine_score, safety_score, text),
        'functional_role': _functional_role(text, machine_score, safety_function_score, safety_score),
        'functional_role_comment': _functional_role_comment(text, machine_score, safety_function_score, safety_score),
        'score_comment': _score_comment(ai_score, safety_score, regulatory_score, baua_score, market_score, criticality_score),
    }


def _combined_patent_text(row):
    fields = ['title', 'abstract']
    parts = [html.unescape(str(row.get(field, '') or '')) for field in fields]
    return ' '.join(parts).lower()


def _extract_ipc_set(row) -> set:
    """Parse the ipc_codes field into a set of trimmed code strings."""
    raw = str(row.get('ipc_codes', '') or '')
    return {c.strip() for c in raw.split(',') if c.strip()}


def _ipc_matches_any(ipc_set: set, prefixes: list) -> bool:
    """True if any code in ipc_set starts with any of the given prefixes."""
    return any(code.startswith(p) for code in ipc_set for p in prefixes)


def _contains_any(text, terms):
    return any(term in text for term in terms)


def _count_matches(text, terms):
    return sum(1 for term in terms if term in text)


def _detect_technology_fields(text, ipc_set=None):
    """Classify patent into technology fields using keywords AND IPC codes."""
    ipc_set = ipc_set or set()
    fields = set()
    # Keyword-based detection (title + abstract)
    for field, keywords in TECHNOLOGY_FIELD_KEYWORDS.items():
        if _contains_any(text, keywords):
            fields.add(field)
    # IPC-based detection — more reliable than keyword guessing
    for field, prefixes in IPC_TECHNOLOGY_MAP.items():
        if _ipc_matches_any(ipc_set, prefixes):
            fields.add(field)
    return sorted(fields) or ['Unclassified']


def _score_ai_relevance(text, ipc_set=None):
    """Score 0-3: how strongly the patent involves AI/ML."""
    ipc_set = ipc_set or set()
    ai_hits = _count_matches(text, AI_TERMS)
    if ai_hits >= 2 and _contains_any(text, ADAPTIVE_AI_TERMS):
        score = 3
    elif ai_hits > 0:
        score = 2
    elif _contains_any(text, ['data', 'recognition', 'classification', 'fusion', 'model', 'controller']):
        score = 1
    else:
        score = 0
    # IPC boost: G06N (neural nets / ML) or G06Q (AI applications) = at least 2
    if _ipc_matches_any(ipc_set, IPC_AI_PREFIXES):
        score = max(score, 2)
    return score


def _score_safety_relevance(text, ipc_set=None):
    """Score 0-3: safety / Arbeitsschutz relevance."""
    ipc_set = ipc_set or set()
    if _contains_any(text, ['emergency', 'collision', 'injury', 'protective', 'safety function', 'safety controller']):
        score = 3
    elif _contains_any(text, SAFETY_TERMS) or (_contains_any(text, MACHINE_TERMS) and 'safety' in text):
        score = 2
    elif _contains_any(text, ['assistance', 'operator', 'human feedback', 'ergonomic', 'monitoring']):
        score = 1
    else:
        score = 0
    # IPC boost: F16P (safety devices), G05B/G05D (control systems with safety scope)
    if _ipc_matches_any(ipc_set, IPC_SAFETY_PREFIXES):
        score = max(score, 2)
    return score


def _score_machine_reference(text, ipc_set=None):
    """Score 0-3: proximity to physical machinery / industrial equipment."""
    ipc_set = ipc_set or set()
    if _contains_any(text, ['robot', 'machinery', 'autonomous machine', 'industrial vehicle', 'work cell']):
        score = 3
    elif _contains_any(text, ['machine', 'industrial', 'production', 'manufacturing', 'vehicle', 'equipment']):
        score = 2
    elif _contains_any(text, ['workplace', 'operator', 'fleet', 'process']):
        score = 1
    else:
        score = 0
    # IPC boost: B25J (robots), B60W/B62D (vehicles), G05B/G05D (industrial control)
    if _ipc_matches_any(ipc_set, IPC_MACHINE_PREFIXES):
        score = max(score, 2)
    # Strongest signal: B25J (robots) → at least 3
    if _ipc_matches_any(ipc_set, ['B25J']):
        score = max(score, 3)
    return score


def _score_safety_function(text, ai_score, ipc_set=None):
    """Score 0-3: whether AI acts as a safety function in the patent."""
    ipc_set = ipc_set or set()
    if ai_score >= 2 and _contains_any(text, SAFETY_FUNCTION_TERMS):
        score = 3
    elif _contains_any(text, SAFETY_FUNCTION_TERMS):
        score = 2
    elif ai_score >= 2 and _contains_any(text, ['control', 'decision', 'monitoring', 'recognition']):
        score = 1
    else:
        score = 0
    # IPC boost: F16P3 (failure-event devices) or B25J9 (programme-controlled robots)
    if _ipc_matches_any(ipc_set, IPC_SAFETY_FUNCTION_PREFIXES) and ai_score >= 1:
        score = max(score, 2)
    return score


def _score_regulatory_relevance(ai_score, safety_score, machine_score, safety_function_score, ipc_set=None):
    """Score 0-3: likely scope of EU AI Act / Machinery Regulation."""
    ipc_set = ipc_set or set()
    if ai_score >= 2 and machine_score >= 2 and (safety_score >= 2 or safety_function_score >= 2):
        score = 3
    elif (ai_score >= 2 and machine_score >= 1) or (machine_score >= 2 and safety_score >= 2):
        score = 2
    elif ai_score >= 1 or safety_score >= 1 or machine_score >= 1:
        score = 1
    else:
        score = 0
    # IPC cross-check: AI code + machine/safety code together = strong regulatory signal
    has_ai_ipc      = bool(ipc_set & {c for c in ipc_set if any(c.startswith(p) for p in IPC_REGULATORY_AI)})
    has_machine_ipc = bool(ipc_set & {c for c in ipc_set if any(c.startswith(p) for p in IPC_REGULATORY_MACHINE)})
    if has_ai_ipc and has_machine_ipc:
        score = max(score, 3)
    elif has_ai_ipc or has_machine_ipc:
        score = max(score, 2)
    return score


def _score_baua_fit(ai_score, safety_score, regulatory_score, machine_score, text):
    if regulatory_score >= 3 or (ai_score >= 2 and safety_score >= 3):
        return 3
    if safety_score >= 2 or (ai_score >= 2 and machine_score >= 2):
        return 2
    if _contains_any(text, ['workplace', 'operator', 'assistance', 'industrial', 'machine', 'human']):
        return 1
    return 0


def _score_market_readiness(text, assignee, is_granted):
    score = 0
    if _contains_any(text, MARKET_NEAR_TERMS):
        score = 2
    elif _contains_any(text, ['method', 'process', 'technique']):
        score = 1
    if is_granted or _contains_any(assignee, MAJOR_INDUSTRIAL_ASSIGNEES):
        score += 1
    return min(score, 3)


def _score_criticality(text, machine_score, safety_function_score):
    high_risk_terms = [
        'collaborative robot', 'robot', 'autonomous machine', 'vehicle', 'collision',
        'person recognition', 'protective', 'shutdown', 'emergency'
    ]
    if safety_function_score >= 3 or _contains_any(text, high_risk_terms):
        return 3
    if machine_score >= 2 and safety_function_score >= 1:
        return 2
    if machine_score >= 1 or safety_function_score >= 1:
        return 1
    return 0


def _priority_category(score):
    if score <= 1.0:
        return 'Beobachten, geringe Prioritaet'
    if score <= 2.0:
        return 'Relevant, gelegentlich pruefen'
    if score <= 2.5:
        return 'Hohe Relevanz'
    return 'Strategischer Watchlist-Kandidat'


def _safety_index_category(score):
    if score < 1.0:
        return 'Gruen: technischer Trend'
    if score < 2.0:
        return 'Gelb: beobachten'
    if score < 2.6:
        return 'Orange: vertieft analysieren'
    return 'Rot: strategische Watchlist'


def _relation_label(score):
    if score >= 3:
        return 'stark'
    if score >= 2:
        return 'plausibel'
    if score >= 1:
        return 'moeglich'
    return 'kein'


def _baua_action_field(baua_score, machine_score, safety_score, text):
    if baua_score >= 3 and machine_score >= 2:
        return 'B Produkt- und Maschinensicherheit'
    if baua_score >= 2 and _contains_any(text, ['human', 'operator', 'workplace', 'assistance', 'interface']):
        return 'C Arbeitssysteme'
    if baua_score >= 2 or safety_score >= 2:
        return 'E Instrumente / KI-Bewertung'
    if baua_score >= 1:
        return 'Allgemeiner Arbeitsweltbezug'
    return 'Kein klarer BAuA-Bezug'


def _functional_role(text, machine_score, safety_function_score, safety_score):
    """
    Classify whether metadata suggests an assistance function or safety component.

    This is a dashboard triage label. It is intentionally conservative and does
    not decide the legal classification under the EU Machinery Regulation.
    """
    safety_component_signal = (
        machine_score >= 2
        and safety_score >= 2
        and (
            safety_function_score >= 2
            or _contains_any(text, SAFETY_COMPONENT_TERMS)
        )
    )
    assistance_signal = _contains_any(text, ASSISTANCE_FUNCTION_TERMS)

    if safety_component_signal and not assistance_signal:
        return 'Sicherheitsbauteil'
    if assistance_signal and not safety_component_signal:
        return 'Assistenzfunktion'
    if safety_component_signal and assistance_signal:
        return 'Unklar'
    return 'Unklar'


def _functional_role_comment(text, machine_score, safety_function_score, safety_score):
    safety_component_signal = (
        machine_score >= 2
        and safety_score >= 2
        and (
            safety_function_score >= 2
            or _contains_any(text, SAFETY_COMPONENT_TERMS)
        )
    )
    assistance_signal = _contains_any(text, ASSISTANCE_FUNCTION_TERMS)

    if safety_component_signal and not assistance_signal:
        return 'Metadaten deuten auf sicherheitsrelevante Maschinen- oder Schutzfunktion hin; rechtlich pruefen.'
    if assistance_signal and not safety_component_signal:
        return 'Metadaten deuten auf Unterstuetzung, Monitoring oder Bedienassistenz ohne klare Schutzfunktion hin.'
    if safety_component_signal and assistance_signal:
        return 'Assistenz- und Schutzfunktionssignale gemischt; Einordnung anhand Patentanspruechen/Abstract pruefen.'
    return 'Keine ausreichenden Metadatensignale fuer Assistenzfunktion oder Sicherheitsbauteil.'


def _score_comment(ai_score, safety_score, regulatory_score, baua_score, market_score, criticality_score):
    drivers = []
    if ai_score >= 2:
        drivers.append('KI/ML erkennbar')
    if safety_score >= 2:
        drivers.append('Arbeitsschutzbezug')
    if regulatory_score >= 2:
        drivers.append('Regulierungsbezug')
    if baua_score >= 2:
        drivers.append('BAuA-Anschluss')
    if criticality_score >= 2:
        drivers.append('Kritikalitaet')
    if market_score >= 2:
        drivers.append('konkrete Umsetzung')
    return ', '.join(drivers) if drivers else 'Keine starken Relevanzsignale aus Metadaten'


def _extract_jurisdiction(patent_id):
    """
    Extract jurisdiction code from patent ID prefix.
    
    Patent ID prefixes:
    - US: United States
    - CN: China
    - JP: Japan
    - EP: European Patent Office
    - DE: Germany
    - KR: South Korea
    - WO: WIPO (World Intellectual Property Organization)
    
    Args:
        patent_id: Patent ID string (e.g., "US20220353664A1")
    
    Returns:
        Jurisdiction code (2-letter), or "Other" if not recognized
    """
    if not isinstance(patent_id, str) or len(patent_id) < 2:
        return "Other"
    
    prefix = patent_id[:2].upper()
    
    known_jurisdictions = {'US', 'CN', 'JP', 'EP', 'DE', 'KR', 'WO'}
    
    if prefix in known_jurisdictions:
        return prefix
    
    # Check for JP format without strict 2-letter prefix
    if prefix.startswith('JP'):
        return 'JP'
    
    return "Other"


def _infer_assignee_country(jurisdiction):
    """
    Infer assignee country from jurisdiction code.
    
    Args:
        jurisdiction: Jurisdiction code (e.g., 'US', 'CN', 'JP')
    
    Returns:
        2-letter country code
    """
    mapping = {
        'US': 'US',
        'CN': 'CN',
        'JP': 'JP',
        'KR': 'KR',
        'DE': 'DE',
        'EP': 'DE',  # European Patent Office → map to DE as primary
        'WO': 'WO',  # WIPO → world
        'Other': 'Other'
    }
    return mapping.get(jurisdiction, 'Other')


def load_assignee_mapping(mapping_path=None):
    """
    Load assignee normalization mapping.
    
    Args:
        mapping_path: Path to assignee_mapping.csv. If None, uses default location.
    
    Returns:
        Dictionary mapping raw names to normalized names
    """
    if mapping_path is None:
        mapping_path = get_project_root() / "data" / "assignee_mapping.csv"
    
    if not Path(mapping_path).exists():
        return {}
    
    mapping_df = pd.read_csv(mapping_path, encoding='utf-8')
    return dict(zip(mapping_df['raw_name'], mapping_df['normalized_name']))


def _normalize_assignee(raw_assignee, mapping=None):
    """
    Normalize assignee name using the mapping table.
    
    Args:
        raw_assignee: Raw assignee name from data
        mapping: Pre-loaded mapping dict (optional, for performance)
    
    Returns:
        Normalized assignee name
    """
    if mapping is None:
        mapping = load_assignee_mapping()
    return mapping.get(raw_assignee, raw_assignee)


def get_unique_values(df, column):
    """
    Get unique values from a column, sorted and with option to include all.
    
    Args:
        df: Patent DataFrame
        column: Column name
    
    Returns:
        Sorted list of unique values
    """
    return sorted(df[column].dropna().unique().tolist())


def filter_by_date_range(df, start_date, end_date, date_column='filing_date'):
    """
    Filter DataFrame by date range.
    
    Args:
        df: Patent DataFrame
        start_date: Start date (datetime or None)
        end_date: End date (datetime or None)
        date_column: Column to filter on ('filing_date' or 'grant_date')
    
    Returns:
        Filtered DataFrame
    """
    filtered = df.copy()
    
    if date_column not in filtered.columns:
        return filtered
    
    if start_date is not None:
        filtered = filtered[filtered[date_column] >= start_date]
    
    if end_date is not None:
        filtered = filtered[filtered[date_column] <= end_date]
    
    return filtered


def filter_by_multi_select(df, column, selected_values):
    """
    Filter DataFrame by multiple selected values in a column.
    
    Args:
        df: Patent DataFrame
        column: Column name
        selected_values: List of values to include
    
    Returns:
        Filtered DataFrame
    """
    if not selected_values:
        return df
    
    return df[df[column].isin(selected_values)]


def filter_by_text(df, search_text, columns=['title', 'assignee', 'assignee_normalized']):
    """
    Filter DataFrame by text search across multiple columns.
    
    Args:
        df: Patent DataFrame
        search_text: Text to search for (case-insensitive)
        columns: Columns to search in
    
    Returns:
        Filtered DataFrame
    """
    if not search_text:
        return df
    
    search_text = search_text.lower()
    mask = False
    
    for col in columns:
        if col in df.columns:
            mask = mask | df[col].astype(str).str.lower().str.contains(search_text, na=False)
    
    return df[mask]


def get_patent_url(patent_id, source='Google Patents'):
    """
    Generate patent URL based on patent ID and source.
    
    Args:
        patent_id: Patent ID string
        source: Source name (currently only Google Patents supported)
    
    Returns:
        Full URL to patent
    """
    if source == 'Google Patents':
        return f"https://patents.google.com/patent/{patent_id}"
    
    return ""


def calculate_statistics(df):
    """
    Calculate overall statistics from patent data.
    
    Args:
        df: Patent DataFrame
    
    Returns:
        Dictionary with statistics
    """
    granted_mask = df['is_granted'] if 'is_granted' in df.columns else df['grant_date'].notna()
    stats = {
        'total_patents': len(df),
        'unique_assignees': df['assignee_normalized'].nunique(),
        'unique_inventors': df['inventor'].nunique(),
        'unique_jurisdictions': df['jurisdiction'].nunique(),
        'patents_with_grants': granted_mask.sum(),
        'patents_pending': (~granted_mask).sum(),
    }
    
    # Filing date range
    if df['filing_date'].notna().any():
        stats['earliest_filing'] = df['filing_date'].min()
        stats['latest_filing'] = df['filing_date'].max()
    
    return stats

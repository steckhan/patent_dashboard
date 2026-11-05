"""
Patent Trends Dashboard - Interactive Streamlit Application

A comprehensive dashboard for analyzing patent intelligence on AI components
with safety functions in machinery, supporting BAuA research.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import sys
import sqlite3
from collections import Counter
import re

# Add src to path to import data_utils
sys.path.insert(0, str(Path(__file__).parent))

from data_utils import (
    load_patent_data,
    filter_by_date_range,
    filter_by_multi_select,
    filter_by_text,
    get_unique_values,
    calculate_statistics,
)
from review_store import DECISIONS, init_reviews, load_reviews, save_review


# Page configuration
st.set_page_config(
    page_title="Patent Trends Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 0.9em;
        color: #666;
    }
    .baua-header {
        background-color: #2c3e50;
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        text-align: center;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Helper functions for new tabs
def extract_keywords_from_titles(df, top_n=20):
    """
    Extract and count keywords from patent titles.
    Removes stopwords and returns top N most common words.
    """
    stopwords = {
        'the', 'a', 'an', 'of', 'for', 'in', 'and', 'with', 'to', 'on',
        'by', 'or', 'is', 'at', 'as', 'from', 'that', 'this', 'using', 'based',
        'und', 'oder', 'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine',
        'einer', 'eines', 'einem', 'einen', 'mit', 'für', 'zur', 'zum', 'von',
        'im', 'in', 'an', 'auf', 'aus', 'bei', 'als', 'durch', 'sowie', 'insbesondere',
        'verfahren', 'vorrichtung', 'system', 'gerät', 'maschine'
    }
    
    all_words = []
    for title in df['title'].dropna():
        # Convert to lowercase and split
        words = title.lower().split()
        # Remove punctuation and filter stopwords
        words = [re.sub(r'[^\w]', '', w) for w in words if w]
        words = [w for w in words if w and w not in stopwords and len(w) > 2]
        all_words.extend(words)
    
    word_counts = Counter(all_words)
    return word_counts.most_common(top_n)


def create_assignee_query_heatmap(df, top_n_assignees=15):
    """
    Create a matrix showing which assignees appear in which queries.
    Returns: (heatmap_df, fig)
    """
    # Get top assignees
    top_assignees = df['assignee_normalized'].value_counts().head(top_n_assignees).index.tolist()
    
    # Get unique queries
    queries = sorted(df['query'].unique())
    
    # Build matrix
    matrix_data = []
    for assignee in top_assignees:
        row = []
        for query in queries:
            count = len(df[(df['assignee_normalized'] == assignee) & (df['query'] == query)])
            row.append(count)
        matrix_data.append(row)
    
    heatmap_df = pd.DataFrame(matrix_data, index=top_assignees, columns=queries)
    return heatmap_df


def create_grant_rate_table(df):
    """
    Create a table showing grant rates by assignee.
    """
    grant_stats = df.groupby('assignee_normalized').agg(
        total_patents=('patent_id', 'count'),
        granted_count=('is_granted', 'sum'),
        avg_grant_lag=('grant_lag_days', 'mean')
    ).reset_index()
    
    # Calculate grant rate
    grant_stats['grant_rate_%'] = (grant_stats['granted_count'] / grant_stats['total_patents'] * 100).round(1)
    grant_stats['avg_grant_lag_days'] = grant_stats['avg_grant_lag'].round(1)
    
    # Drop the avg_grant_lag column and sort
    grant_stats = grant_stats.drop('avg_grant_lag', axis=1)
    grant_stats = grant_stats.sort_values('total_patents', ascending=False)
    
    return grant_stats


def _data_file_signature():
    """Track each input file so changes to either source invalidate the cache."""
    from pathlib import Path
    data_dir = Path(__file__).parent.parent / "data"
    candidates = list(data_dir.glob("patente_*.csv")) + list(data_dir.glob("*.xlsx"))
    return tuple(sorted((str(path), path.stat().st_mtime_ns, path.stat().st_size) for path in candidates))


@st.cache_data
def load_data(data_signature=()):
    """Load patent data, invalidating the cache when an input file changes."""
    try:
        df = load_patent_data()
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


def apply_filters(df):
    """Apply sidebar filters and return filtered DataFrame."""
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filters")
    
    filtered_df = df.copy()

    # Record level filter
    if 'record_level' in df.columns:
        st.sidebar.subheader("Record Level")
        record_levels = get_unique_values(df, 'record_level')
        selected_record_levels = st.sidebar.multiselect(
            "Select record levels",
            options=record_levels,
            default=record_levels,
            key="record_levels"
        )
        filtered_df = filter_by_multi_select(filtered_df, 'record_level', selected_record_levels)
    else:
        selected_record_levels = []
    
    # Date range filter
    st.sidebar.subheader("Filing Date Range")
    min_date = filtered_df['filing_date'].min()
    max_date = filtered_df['filing_date'].max()
    
    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.sidebar.slider(
            "Select date range",
            min_value=min_date.date(),
            max_value=max_date.date(),
            value=(min_date.date(), max_date.date()),
            key="date_range"
        )
        filtered_df = filter_by_date_range(
            filtered_df,
            pd.Timestamp(date_range[0]),
            pd.Timestamp(date_range[1]),
            'filing_date'
        )
    
    # Source filter
    st.sidebar.subheader("Source")
    sources = get_unique_values(df, 'source')
    selected_sources = st.sidebar.multiselect(
        "Select sources",
        options=sources,
        default=sources,
        key="sources"
    )
    filtered_df = filter_by_multi_select(filtered_df, 'source', selected_sources)
    
    # Assignee filter
    st.sidebar.subheader("Assignee")
    assignees = sorted(df['assignee_normalized'].unique().tolist())
    selected_assignees = st.sidebar.multiselect(
        "Select assignees (normalized)",
        options=assignees,
        key="assignees"
    )
    if selected_assignees:
        filtered_df = filter_by_multi_select(filtered_df, 'assignee_normalized', selected_assignees)
    
    # Jurisdiction filter
    st.sidebar.subheader("Jurisdiction")
    jurisdictions = get_unique_values(df, 'jurisdiction')
    selected_jurisdictions = st.sidebar.multiselect(
        "Select jurisdictions",
        options=jurisdictions,
        default=jurisdictions,
        key="jurisdictions"
    )
    filtered_df = filter_by_multi_select(filtered_df, 'jurisdiction', selected_jurisdictions)
    
    # Search query filter
    st.sidebar.subheader("Search Query")
    queries = get_unique_values(df, 'query')
    selected_queries = st.sidebar.multiselect(
        "Select queries",
        options=queries,
        key="queries"
    )
    if selected_queries:
        filtered_df = filter_by_multi_select(filtered_df, 'query', selected_queries)

    # BAuA priority filter
    if 'priority_category' in df.columns:
        st.sidebar.subheader("BAuA Priority")
        priority_options = get_unique_values(df, 'priority_category')
        selected_priorities = st.sidebar.multiselect(
            "Select priority categories",
            options=priority_options,
            key="priorities"
        )
        if selected_priorities:
            filtered_df = filter_by_multi_select(filtered_df, 'priority_category', selected_priorities)
    else:
        selected_priorities = []

    # Technology field filter
    if 'technology_fields' in df.columns:
        st.sidebar.subheader("Technology Field")
        tech_options = sorted({
            field.strip()
            for value in df['technology_fields'].dropna()
            for field in str(value).split(',')
            if field.strip()
        })
        selected_tech_fields = st.sidebar.multiselect(
            "Select technology fields",
            options=tech_options,
            key="technology_fields"
        )
        if selected_tech_fields:
            tech_pattern = '|'.join(re.escape(field) for field in selected_tech_fields)
            filtered_df = filtered_df[
                filtered_df['technology_fields'].astype(str).str.contains(tech_pattern, case=False, na=False)
            ]
    else:
        selected_tech_fields = []

    # Priority score range
    if 'patent_priority_score' in df.columns:
        st.sidebar.subheader("Priority Score")
        score_min, score_max = st.sidebar.slider(
            "Patent Priority Score",
            min_value=0.0,
            max_value=3.0,
            value=(0.0, 3.0),
            step=0.1,
            key="priority_score_range"
        )
        filtered_df = filtered_df[
            (filtered_df['patent_priority_score'] >= score_min)
            & (filtered_df['patent_priority_score'] <= score_max)
        ]
    else:
        score_min, score_max = 0.0, 3.0

    # Functional role filter
    if 'functional_role' in df.columns:
        st.sidebar.subheader("Functional Role")
        role_options = get_unique_values(df, 'functional_role')
        selected_roles = st.sidebar.multiselect(
            "Select function classification",
            options=role_options,
            key="functional_roles"
        )
        if selected_roles:
            filtered_df = filter_by_multi_select(filtered_df, 'functional_role', selected_roles)
    else:
        selected_roles = []

    if 'family_legal_status' in df.columns:
        family_status_options = get_unique_values(df[df['family_legal_status'].notna()], 'family_legal_status')
        if family_status_options:
            st.sidebar.subheader("Family Legal Status")
            selected_family_statuses = st.sidebar.multiselect(
                "Select family statuses",
                options=family_status_options,
                key="family_legal_statuses"
            )
            if selected_family_statuses:
                filtered_df = filter_by_multi_select(filtered_df, 'family_legal_status', selected_family_statuses)
        else:
            selected_family_statuses = []
    else:
        selected_family_statuses = []

    if 'family_legal_state' in df.columns:
        family_state_options = get_unique_values(df[df['family_legal_state'].notna()], 'family_legal_state')
        if family_state_options:
            st.sidebar.subheader("Family Legal State")
            selected_family_states = st.sidebar.multiselect(
                "Select family states",
                options=family_state_options,
                key="family_legal_states"
            )
            if selected_family_states:
                filtered_df = filter_by_multi_select(filtered_df, 'family_legal_state', selected_family_states)
        else:
            selected_family_states = []
    else:
        selected_family_states = []

    marker_columns = {
        'marker_person': 'Person',
        'marker_robot': 'Roboter',
        'marker_ml_vision': 'ML/Bildauswertung',
        'marker_stop': 'Stop',
        'marker_safety': 'Schutz/Sicherheit',
        'marker_ai': 'KI',
        'marker_hazard': 'Gefahr',
        'marker_industrial_machine': 'Industriemaschine',
        'marker_camera': 'Kamera',
    }
    available_markers = {col: label for col, label in marker_columns.items() if col in df.columns}
    if available_markers:
        st.sidebar.subheader("Orbit/FAMPAT Markers")
        selected_markers = st.sidebar.multiselect(
            "Require markers",
            options=list(available_markers.keys()),
            format_func=lambda col: available_markers[col],
            key="required_markers"
        )
        for marker_col in selected_markers:
            filtered_df = filtered_df[filtered_df[marker_col].fillna(False)]
    else:
        selected_markers = []
    
    return filtered_df, {
        'date_range': date_range if pd.notna(min_date) else None,
        'sources': selected_sources,
        'record_levels': selected_record_levels,
        'assignees': selected_assignees,
        'jurisdictions': selected_jurisdictions,
        'queries': selected_queries,
        'priorities': selected_priorities,
        'technology_fields': selected_tech_fields,
        'priority_score_range': (score_min, score_max),
        'functional_roles': selected_roles,
        'family_legal_statuses': selected_family_statuses,
        'family_legal_states': selected_family_states,
        'required_markers': selected_markers,
    }


def render_header():
    """Render dashboard header with BAuA branding."""
    # BAuA sidebar header
    st.sidebar.markdown(
        '<div class="baua-header">🔬 Patent Trends Dashboard</div>',
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📊 Patent Trends Dashboard")
        st.markdown("Interactive analysis of AI patents with safety functions in machinery")
    with col2:
        st.markdown("")
        st.markdown("")
        st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def render_overview_metrics(df):
    """Render overview metric cards with abstract availability warning and key insights."""
    stats = calculate_statistics(df)
    
    # Abstract availability warning
    abstracts_available = df['abstract'].notna().sum()
    if abstracts_available == 0:
        st.info("⚠️ Abstracts are not available in this dataset.")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Patents", stats['total_patents'])
    with col2:
        st.metric("Unique Assignees", stats['unique_assignees'])
    with col3:
        st.metric("Granted Patents", stats['patents_with_grants'])
    with col4:
        st.metric("Pending Patents", stats['patents_pending'])

    if 'patent_priority_score' in df.columns:
        score_col1, score_col2, score_col3, score_col4 = st.columns(4)
        with score_col1:
            st.metric("Avg Priority Score", f"{df['patent_priority_score'].mean():.2f}")
        with score_col2:
            watchlist_count = (df['priority_category'] == 'Strategischer Watchlist-Kandidat').sum()
            st.metric("Watchlist Candidates", int(watchlist_count))
        with score_col3:
            high_count = df['priority_category'].isin([
                'Hohe Relevanz',
                'Strategischer Watchlist-Kandidat'
            ]).sum()
            st.metric("High Relevance", int(high_count))
        with score_col4:
            st.metric("Avg Safety Index", f"{df['industrial_ai_safety_index'].mean():.2f}")

            if 'functional_role' in df.columns:
                role_counts = df['functional_role'].value_counts()
                role_summary = ', '.join(f"{role}: {count}" for role, count in role_counts.items())
                st.caption(f"Function role: {role_summary}")
    
    # Key Insight callout
    if len(df) > 0:
        top_assignee = df['assignee_normalized'].value_counts().index[0]
        top_assignee_count = df['assignee_normalized'].value_counts().iloc[0]
        top_year = df['year_filed'].mode()[0] if len(df['year_filed'].dropna()) > 0 else 'N/A'
        
        # Calculate grant rate
        total_granted = df['is_granted'].sum()
        total_patents = len(df)
        grant_rate = (total_granted / total_patents * 100) if total_patents > 0 else 0
        
        insight_text = f"Top filer: **{top_assignee}** with {top_assignee_count} patents. Most active year: **{top_year}**. Grant rate: **{grant_rate:.0f}%**."
        if 'patent_priority_score' in df.columns:
            top_priority = df.sort_values('patent_priority_score', ascending=False).iloc[0]
            insight_text += f" Highest-priority patent: **{top_priority['patent_id']}** ({top_priority['patent_priority_score']:.2f})."
        st.info(f"💡 **Key Insight:** {insight_text}")


def render_trend_dashboard(df):
    """View 1: Trend Dashboard - Filing and grant timeline analysis."""
    st.header("📈 Trend Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Filing timeline by year
        filing_by_year = df.groupby(df['filing_date'].dt.year).size().reset_index(name='count')
        filing_by_year.columns = ['year', 'count']
        
        fig_filing = px.bar(
            filing_by_year,
            x='year',
            y='count',
            title='Patents Filed by Year',
            labels={'year': 'Year', 'count': 'Number of Patents'},
            color='count',
            color_continuous_scale='Blues'
        )
        fig_filing.update_layout(height=400)
        st.plotly_chart(fig_filing, use_container_width=True)
    
    with col2:
        # Grant timeline by year (only granted patents)
        grant_data = df[df['grant_date'].notna()].copy()
        grant_by_year = grant_data.groupby(grant_data['grant_date'].dt.year).size().reset_index(name='count')
        grant_by_year.columns = ['year', 'count']
        
        fig_grant = px.bar(
            grant_by_year,
            x='year',
            y='count',
            title='Patents Granted by Year',
            labels={'year': 'Year', 'count': 'Number of Patents'},
            color='count',
            color_continuous_scale='Greens'
        )
        fig_grant.update_layout(height=400)
        st.plotly_chart(fig_grant, use_container_width=True)
    
    # Quarterly filing trend
    df_with_dates = df.dropna(subset=['filing_date']).copy()
    if len(df_with_dates) > 0:
        quarterly_data = df_with_dates.set_index('filing_date').resample('QE').size().reset_index()
        quarterly_data.columns = ['quarter', 'count']
        
        fig_quarterly = px.line(
            quarterly_data,
            x='quarter',
            y='count',
            title='Patents Filed by Quarter',
            labels={'quarter': 'Quarter', 'count': 'Number of Patents'},
            markers=True,
            color_discrete_sequence=['#EF553B']
        )
        fig_quarterly.update_layout(height=400)
        st.plotly_chart(fig_quarterly, use_container_width=True)
    
    # Grant Rate Over Time
    if 'is_granted' in df.columns:
        grant_rate_by_year = df.groupby('year_filed').agg(
            total=('patent_id', 'count'),
            granted=('is_granted', 'sum')
        ).reset_index()
        grant_rate_by_year = grant_rate_by_year.dropna(subset=['year_filed'])
        grant_rate_by_year['grant_rate_%'] = (grant_rate_by_year['granted'] / grant_rate_by_year['total'] * 100).round(1)
        
        fig_grant_rate = px.line(
            grant_rate_by_year,
            x='year_filed',
            y='grant_rate_%',
            title='Grant Rate Over Time',
            labels={'year_filed': 'Year Filed', 'grant_rate_%': 'Grant Rate (%)'},
            markers=True,
            color_discrete_sequence=['#00CC96']
        )
        fig_grant_rate.update_layout(height=400)
        st.plotly_chart(fig_grant_rate, use_container_width=True)
    
    # Cumulative count area chart
    cumulative_by_year = df.groupby(df['filing_date'].dt.year).size().reset_index(name='count')
    cumulative_by_year.columns = ['year', 'count']
    cumulative_by_year['cumulative'] = cumulative_by_year['count'].cumsum()
    
    fig_cumulative = px.area(
        cumulative_by_year,
        x='year',
        y='cumulative',
        title='Cumulative Patent Filings Over Time',
        labels={'year': 'Year', 'cumulative': 'Cumulative Patents'},
        color_discrete_sequence=['#636EFA']
    )
    fig_cumulative.update_layout(height=400)
    st.plotly_chart(fig_cumulative, use_container_width=True)


def render_assignee_landscape(df):
    """View 2: Assignee Landscape - Top assignees and normalization."""
    st.header("🏢 Assignee Landscape")
    
    # Top assignees by normalized name
    top_assignees = df['assignee_normalized'].value_counts().head(15)
    
    fig_assignees = px.bar(
        x=top_assignees.values,
        y=top_assignees.index,
        orientation='h',
        title='Top 15 Assignees (Normalized)',
        labels={'x': 'Number of Patents', 'y': 'Assignee'},
        color=top_assignees.values,
        color_continuous_scale='Viridis'
    )
    fig_assignees.update_yaxes(categoryorder='total ascending')
    fig_assignees.update_layout(height=500)
    st.plotly_chart(fig_assignees, use_container_width=True)
    
    # Show comparison of raw vs normalized names
    st.subheader("Raw vs. Normalized Assignee Names")
    
    comparison_data = []
    for raw_name in df['assignee'].unique():
        normalized = df[df['assignee'] == raw_name]['assignee_normalized'].iloc[0]
        count = len(df[df['assignee'] == raw_name])
        if count > 0:
            comparison_data.append({
                'Raw Name': raw_name,
                'Normalized Name': normalized,
                'Patent Count': count
            })
    
    comparison_df = pd.DataFrame(comparison_data).sort_values('Patent Count', ascending=False)
    
    # Show only the assignees that got normalized (different raw vs normalized)
    normalized_only = comparison_df[comparison_df['Raw Name'] != comparison_df['Normalized Name']]
    
    if len(normalized_only) > 0:
        st.dataframe(
            normalized_only.reset_index(drop=True),
            use_container_width=True,
            height=300
        )
    else:
        st.info("No assignee normalization applied to this filtered dataset.")


def render_jurisdiction_analysis(df):
    """View 3: Jurisdiction Analysis - Geographic distribution with choropleth."""
    st.header("🌍 Jurisdiction Analysis")
    
    # Prepare data for choropleth map
    # Map jurisdiction codes to ISO 3166-1 alpha-3 codes for choropleth
    iso_mapping = {
        'US': 'USA',
        'CN': 'CHN',
        'JP': 'JPN',
        'DE': 'DEU',
        'KR': 'KOR',
    }
    
    jurisdiction_counts = df['jurisdiction'].value_counts().reset_index()
    jurisdiction_counts.columns = ['jurisdiction', 'count']
    
    # Filter for mappable jurisdictions
    mappable_data = jurisdiction_counts[jurisdiction_counts['jurisdiction'].isin(iso_mapping.keys())].copy()
    mappable_data['iso_code'] = mappable_data['jurisdiction'].map(iso_mapping)
    
    if len(mappable_data) > 0:
        fig_choropleth = px.choropleth(
            mappable_data,
            locations='iso_code',
            color='count',
            title='Patent Distribution by Jurisdiction',
            labels={'count': 'Number of Patents'},
            color_continuous_scale='Blues',
            scope='world'
        )
        fig_choropleth.update_layout(height=500)
        st.plotly_chart(fig_choropleth, use_container_width=True)
    
    # Full jurisdiction table with percentages (including EP, WO, Other)
    jurisdiction_table = df['jurisdiction'].value_counts().reset_index()
    jurisdiction_table.columns = ['Jurisdiction', 'Count']
    jurisdiction_table['Percentage'] = (jurisdiction_table['Count'] / jurisdiction_table['Count'].sum() * 100).round(1)
    
    st.subheader("Jurisdiction Breakdown")
    st.dataframe(
        jurisdiction_table,
        use_container_width=True,
        height=300
    )


def render_query_performance(df):
    """View 4: Query Performance - Search query analysis and overlap."""
    st.header("🔎 Query Performance & Coverage")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Patents per query
        query_counts = df['query'].value_counts()
        
        fig_queries = px.bar(
            x=query_counts.index,
            y=query_counts.values,
            title='Patents per Search Query',
            labels={'x': 'Query', 'y': 'Number of Patents'},
            color=query_counts.values,
            color_continuous_scale='Teal'
        )
        fig_queries.update_xaxes(tickangle=45)
        fig_queries.update_layout(height=400)
        st.plotly_chart(fig_queries, use_container_width=True)
    
    with col2:
        # Query overlap analysis
        st.subheader("Query Overlap Analysis")
        
        query_overlap = []
        unique_queries = df['query'].unique()
        
        for query in sorted(unique_queries):
            patents_in_query = set(df[df['query'] == query]['patent_id'])
            query_overlap.append({
                'Query': query,
                'Unique Patents': len(patents_in_query),
                'Total Hits': len(df[df['query'] == query])
            })
        
        overlap_df = pd.DataFrame(query_overlap)
        st.dataframe(overlap_df, use_container_width=True)
        
        # Patent deduplication stats
        total_hits = len(df)
        unique_patents = df['patent_id'].nunique()
        duplicate_ratio = ((total_hits - unique_patents) / total_hits * 100) if total_hits > 0 else 0
        
        st.metric(
            "Unique Patents (across all queries)",
            unique_patents,
            delta=f"{duplicate_ratio:.1f}% redundancy across queries"
        )


def render_competitive_intel(df):
    """View 6: Competitive Intel - Patent portfolio analysis by assignee."""
    st.header("🏆 Competitive Intelligence")
    
    # Treemap: Patent portfolio by company
    treemap_data = df.groupby(['assignee_normalized', 'jurisdiction']).size().reset_index(name='count')
    
    fig_treemap = px.treemap(
        treemap_data,
        path=['assignee_normalized', 'jurisdiction'],
        values='count',
        title='Patent Portfolio by Company & Jurisdiction',
        color='count',
        color_continuous_scale='RdYlGn'
    )
    fig_treemap.update_layout(height=500)
    st.plotly_chart(fig_treemap, use_container_width=True)
    
    # Bubble chart: Innovation velocity
    bubble_data = df.groupby(['year_filed', 'assignee_normalized']).size().reset_index(name='count')
    bubble_data = bubble_data.dropna(subset=['year_filed'])
    
    # Limit to top 10 assignees for clarity
    top_assignees = df['assignee_normalized'].value_counts().head(10).index
    bubble_data_filtered = bubble_data[bubble_data['assignee_normalized'].isin(top_assignees)]
    
    fig_bubble = px.scatter(
        bubble_data_filtered,
        x='year_filed',
        y='assignee_normalized',
        size='count',
        hover_data=['count'],
        title='Innovation Velocity: Patents by Company Over Time (Top 10)',
        labels={'year_filed': 'Year Filed', 'assignee_normalized': 'Assignee', 'count': 'Patent Count'},
        color='count',
        color_continuous_scale='Viridis',
        size_max=50
    )
    fig_bubble.update_layout(height=500)
    st.plotly_chart(fig_bubble, use_container_width=True)
    
    # Grant rate table
    grant_table = create_grant_rate_table(df)
    
    st.subheader("Grant Rate Analysis by Company")
    st.dataframe(
        grant_table,
        use_container_width=True,
        height=400
    )


def render_abstract_intelligence(df):
    """View 7: Abstract Intelligence - Keyword analysis and search coverage."""
    st.header("📝 Abstract Intelligence")
    
    # Top keywords from titles
    st.subheader("Top Keywords from Patent Titles")
    
    top_keywords = extract_keywords_from_titles(df, top_n=20)
    
    if top_keywords:
        keywords_df = pd.DataFrame(top_keywords, columns=['word', 'frequency'])
        
        fig_keywords = px.bar(
            keywords_df,
            x='frequency',
            y='word',
            orientation='h',
            title='Top 20 Keywords in Patent Titles',
            labels={'word': 'Keyword', 'frequency': 'Frequency'},
            color='frequency',
            color_continuous_scale='Plasma'
        )
        fig_keywords.update_yaxes(categoryorder='total ascending')
        fig_keywords.update_layout(height=500)
        st.plotly_chart(fig_keywords, use_container_width=True)
    else:
        st.info("No keywords found in patents.")
    
    # Assignee-Query coverage heatmap
    st.subheader("Search Query Coverage Matrix")
    st.markdown("Shows which assignees appear in which search queries (number of patents).")
    
    heatmap_df = create_assignee_query_heatmap(df, top_n_assignees=15)
    
    fig_heatmap = px.imshow(
        heatmap_df,
        title='Assignee-Query Coverage Heatmap (Top 15 Assignees)',
        labels=dict(x='Query', y='Assignee', color='Patent Count'),
        color_continuous_scale='YlOrRd',
        aspect='auto'
    )
    fig_heatmap.update_layout(height=500)
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    st.dataframe(
        heatmap_df.reset_index().rename(columns={'index': 'Assignee'}),
        use_container_width=True,
        height=400
    )


def render_regulatory_relevance(df):
    """View: BAuA and regulatory relevance scoring."""
    st.header("⚖️ Regulatory & BAuA Relevance")
    st.markdown(
        "Prioritization layer for patents that may matter for safe, human-centered and regulation-compliant Industrial AI systems."
    )

    score_columns = [
        'ai_relevance_score',
        'safety_relevance_score',
        'regulatory_relevance_score',
        'baua_fit_score',
        'market_readiness_score',
        'criticality_score',
    ]
    available_scores = [col for col in score_columns if col in df.columns]
    if not available_scores:
        st.info("No regulatory scoring columns available.")
        return

    col1, col2 = st.columns(2)

    with col1:
        priority_counts = df['priority_category'].value_counts().reset_index()
        priority_counts.columns = ['priority_category', 'count']
        fig_priority = px.bar(
            priority_counts,
            x='priority_category',
            y='count',
            title='Patent Priority Categories',
            labels={'priority_category': 'Priority', 'count': 'Number of Patents'},
            color='count',
            color_continuous_scale='Oranges'
        )
        fig_priority.update_xaxes(tickangle=30)
        fig_priority.update_layout(height=420)
        st.plotly_chart(fig_priority, use_container_width=True)

    with col2:
        safety_counts = df['safety_index_category'].value_counts().reset_index()
        safety_counts.columns = ['safety_index_category', 'count']
        fig_safety = px.bar(
            safety_counts,
            x='safety_index_category',
            y='count',
            title='Industrial AI Safety Relevance Index',
            labels={'safety_index_category': 'Index Category', 'count': 'Number of Patents'},
            color='count',
            color_continuous_scale='RdYlGn_r'
        )
        fig_safety.update_xaxes(tickangle=30)
        fig_safety.update_layout(height=420)
        st.plotly_chart(fig_safety, use_container_width=True)

    if 'functional_role' in df.columns:
        role_counts = df['functional_role'].value_counts().reset_index()
        role_counts.columns = ['functional_role', 'count']
        fig_roles = px.pie(
            role_counts,
            names='functional_role',
            values='count',
            title='Assistenzfunktion vs. Sicherheitsbauteil vs. Unklar',
            hole=0.35
        )
        fig_roles.update_layout(height=420)
        st.plotly_chart(fig_roles, use_container_width=True)

    score_means = df[available_scores].mean().reset_index()
    score_means.columns = ['dimension', 'average_score']
    score_means['dimension'] = score_means['dimension'].str.replace('_score', '').str.replace('_', ' ').str.title()

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=score_means['average_score'],
        theta=score_means['dimension'],
        fill='toself',
        name='Average Score'
    ))
    fig_radar.update_layout(
        title='Average Relevance Profile',
        polar=dict(radialaxis=dict(visible=True, range=[0, 3])),
        height=500
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    st.subheader("Top Watchlist Candidates")
    watchlist_columns = [
        'patent_id',
        'title',
        'assignee_normalized',
        'technology_fields',
        'patent_priority_score',
        'industrial_ai_safety_index',
        'priority_category',
        'functional_role',
        'ai_act_relation',
        'machinery_regulation_relation',
        'baua_action_field',
        'functional_role_comment',
        'score_comment',
    ]
    watchlist_columns = [col for col in watchlist_columns if col in df.columns]
    watchlist_df = df.sort_values(
        ['patent_priority_score', 'industrial_ai_safety_index'],
        ascending=False
    )[watchlist_columns].head(20)
    st.dataframe(watchlist_df, use_container_width=True, height=460)

    st.subheader("Technology Fields by Priority")
    exploded = df.assign(
        technology_field=df['technology_fields'].astype(str).str.split(', ')
    ).explode('technology_field')
    tech_priority = exploded.groupby(['technology_field', 'priority_category']).size().reset_index(name='count')
    if len(tech_priority) > 0:
        fig_tech_priority = px.bar(
            tech_priority,
            x='technology_field',
            y='count',
            color='priority_category',
            title='Technology Fields and Priority Categories',
            labels={'technology_field': 'Technology Field', 'count': 'Number of Patents'},
        )
        fig_tech_priority.update_xaxes(tickangle=35)
        fig_tech_priority.update_layout(height=500)
        st.plotly_chart(fig_tech_priority, use_container_width=True)

    with st.expander("Scoring model"):
        st.markdown(
            """
            Scores run from 0 to 3. The weighted Patent Priority Score uses:
            KI-Relevanz 20%, Safety/Arbeitsschutz 25%, Regulierungsbezug 20%,
            BAuA-Anschlussfähigkeit 20%, Marktnähe 10%, Kritikalität 5%.

            The Industrial AI Safety Relevance Index emphasizes KI as safety-relevant
            component, machine/work-equipment proximity, potential worker impact,
            regulatory relevance and BAuA fit. Current scoring is heuristic because
            the dataset does not yet include abstracts or IPC codes.
            """
        )


def render_family_intelligence(df):
    """View: Orbit/FAMPAT family-level status and marker analysis."""
    st.header("👪 Family Intelligence")

    if 'record_level' not in df.columns:
        st.info("No patent-family records available.")
        return

    family_df = df[df['record_level'] == 'Patent Family'].copy()
    if family_df.empty:
        st.info("No Orbit/FAMPAT patent-family records match the current filters.")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Patent Families", len(family_df))
    with col2:
        st.metric("Alive Families", int((family_df.get('family_legal_state') == 'ALIVE').sum()))
    with col3:
        st.metric("Granted Families", int((family_df.get('family_legal_status') == 'GRANTED').sum()))
    with col4:
        avg_family_size = family_df['family_member_count'].mean() if 'family_member_count' in family_df.columns else 0
        st.metric("Avg Family Size", f"{avg_family_size:.1f}")

    col1, col2 = st.columns(2)
    with col1:
        status_counts = family_df['family_legal_status'].value_counts().reset_index()
        status_counts.columns = ['family_legal_status', 'count']
        fig_status = px.bar(
            status_counts,
            x='family_legal_status',
            y='count',
            title='Family Legal Status',
            labels={'family_legal_status': 'Legal Status', 'count': 'Patent Families'},
            color='count',
            color_continuous_scale='Blues'
        )
        fig_status.update_layout(height=400)
        st.plotly_chart(fig_status, use_container_width=True)

    with col2:
        state_counts = family_df['family_legal_state'].value_counts().reset_index()
        state_counts.columns = ['family_legal_state', 'count']
        fig_state = px.pie(
            state_counts,
            names='family_legal_state',
            values='count',
            title='Family Legal State',
            hole=0.35
        )
        fig_state.update_layout(height=400)
        st.plotly_chart(fig_state, use_container_width=True)

    marker_columns = {
        'marker_person': 'Person',
        'marker_robot': 'Roboter',
        'marker_ml_vision': 'ML/Bildauswertung',
        'marker_stop': 'Stop',
        'marker_safety': 'Schutz/Sicherheit',
        'marker_ai': 'KI',
        'marker_hazard': 'Gefahr',
        'marker_industrial_machine': 'Industriemaschine',
        'marker_camera': 'Kamera',
    }
    available_markers = {col: label for col, label in marker_columns.items() if col in family_df.columns}
    if available_markers:
        marker_counts = pd.DataFrame([
            {'Marker': label, 'Count': int(family_df[col].fillna(False).sum())}
            for col, label in available_markers.items()
        ]).sort_values('Count', ascending=True)
        fig_markers = px.bar(
            marker_counts,
            x='Count',
            y='Marker',
            orientation='h',
            title='Orbit/FAMPAT Marker Frequency',
            color='Count',
            color_continuous_scale='Oranges'
        )
        fig_markers.update_layout(height=450)
        st.plotly_chart(fig_markers, use_container_width=True)

        marker_matrix = family_df[list(available_markers.keys())].fillna(False).astype(int)
        cooccurrence = marker_matrix.T.dot(marker_matrix)
        cooccurrence.index = [available_markers[col] for col in cooccurrence.index]
        cooccurrence.columns = [available_markers[col] for col in cooccurrence.columns]
        fig_cooccurrence = px.imshow(
            cooccurrence,
            title='Marker Co-occurrence',
            labels=dict(x='Marker', y='Marker', color='Families'),
            color_continuous_scale='YlOrRd',
            aspect='auto'
        )
        fig_cooccurrence.update_layout(height=550)
        st.plotly_chart(fig_cooccurrence, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        top_applicants = family_df['assignee_normalized'].value_counts().head(15).reset_index()
        top_applicants.columns = ['Applicant', 'Patent Families']
        st.subheader("Top Applicants")
        st.dataframe(top_applicants, use_container_width=True, height=420)

    with col2:
        if 'family_member_count' in family_df.columns:
            fig_family_size = px.histogram(
                family_df,
                x='family_member_count',
                title='Family Member Count Distribution',
                labels={'family_member_count': 'Family Members'},
                nbins=12
            )
            fig_family_size.update_layout(height=420)
            st.plotly_chart(fig_family_size, use_container_width=True)


def render_review_queue(df, reviews):
    """Review source records one at a time and export annotated research results."""
    st.header("📝 Review Queue")
    st.caption("Human assessments are saved locally; automated priority scores are screening aids only.")

    # The same publication can appear in multiple search results; review each source record once.
    records = df.drop_duplicates(subset=['source', 'record_level', 'patent_id']).copy()
    if records.empty:
        st.info("No records match the dashboard filters.")
        return

    def record_key(row):
        return (str(row['source']), str(row['record_level']), str(row['patent_id']))

    records['review_decision'] = [
        reviews.get(record_key(row), {}).get('decision', 'Unreviewed')
        for _, row in records.iterrows()
    ]
    records['on_watchlist'] = [
        bool(reviews.get(record_key(row), {}).get('watchlist', False))
        for _, row in records.iterrows()
    ]
    reviewed = int((records['review_decision'] != 'Unreviewed').sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reviewed", reviewed)
    c2.metric("Remaining", len(records) - reviewed)
    c3.metric("Relevant", int((records['review_decision'] == 'Relevant').sum()))
    c4.metric("On Watchlist", int(records['on_watchlist'].sum()))
    st.progress(reviewed / len(records))

    view = st.radio(
        "Queue", ['Unreviewed', 'Needs follow-up', 'Relevant', 'Not relevant', 'Watchlist', 'All'],
        horizontal=True, key='review_queue_view'
    )
    search = st.text_input("Find a record", placeholder="Patent ID, title or applicant", key='review_search')
    queue = records if view == 'All' else records[
        records['on_watchlist'] if view == 'Watchlist' else records['review_decision'] == view
    ]
    if search:
        mask = (
            queue['patent_id'].astype(str).str.contains(search, case=False, regex=False, na=False)
            | queue['title'].astype(str).str.contains(search, case=False, regex=False, na=False)
            | queue['assignee_normalized'].astype(str).str.contains(search, case=False, regex=False, na=False)
        )
        queue = queue[mask]
    queue = queue.sort_values('patent_priority_score', ascending=False, na_position='last')

    if queue.empty:
        st.info("No records in this queue. Choose another view or adjust your filters.")
    else:
        by_key = {record_key(row): row for _, row in queue.iterrows()}
        keys = list(by_key)
        selected = st.selectbox(
            f"Select record ({len(keys)} results)", keys,
            format_func=lambda key: f"{key[2]} · {str(by_key[key]['title'])[:75]} · {key[0]} ({key[1]})",
            key='review_selected'
        )
        row = by_key[selected]
        existing = reviews.get(selected, {})

        st.subheader(str(row['title']))
        st.caption(f"{row['assignee_normalized']} · {selected[0]} · {selected[1]} · {selected[2]}")
        if pd.notna(row.get('url')) and str(row['url']).startswith('http'):
            st.link_button("Open source record", str(row['url']))
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Heuristic priority score:** {row.get('patent_priority_score', 'n/a')}")
            st.write(f"**Score rationale:** {row.get('score_comment', 'n/a')}")
            st.write(f"**Technology fields:** {row.get('technology_fields', 'n/a')}")
        with col2:
            st.write(f"**Jurisdiction:** {row.get('jurisdiction', 'n/a')}")
            if selected[1] == 'Patent Family':
                st.write(f"**Family status:** {row.get('family_legal_status', 'n/a')}")
                st.write(f"**Family state:** {row.get('family_legal_state', 'n/a')}")
                st.write(f"**Family members:** {row.get('family_members', 'n/a')}")
            else:
                st.write(f"**Filing date:** {row.get('filing_date', 'n/a')}")
        if isinstance(row.get('abstract'), str) and row['abstract'].strip():
            with st.expander("Abstract"):
                st.write(row['abstract'])

        with st.form(f"review_form_{selected[0]}_{selected[1]}_{selected[2]}"):
            decision = st.selectbox("Researcher decision", DECISIONS,
                                    index=DECISIONS.index(existing.get('decision', 'Unreviewed')))
            rationale = st.text_area("Rationale / evidence", value=existing.get('rationale', ''))
            tags = st.text_input("Tags (comma-separated)", value=existing.get('tags', ''))
            watchlist = st.checkbox("Add to watchlist", value=bool(existing.get('watchlist', False)))
            next_action = st.text_input("Next action", value=existing.get('next_action', ''))
            submitted = st.form_submit_button("Save assessment", type='primary')
        if submitted:
            save_review(*selected, decision, rationale, tags, watchlist, next_action)
            st.rerun()
        def select_next_record():
            st.session_state['review_selected'] = keys[(keys.index(selected) + 1) % len(keys)]

        st.button("Next record", disabled=len(keys) < 2, on_click=select_next_record)
        if existing.get('reviewed_at'):
            st.caption(f"Last reviewed: {existing['reviewed_at']}")

    st.subheader("Export assessments")
    export = records[['source', 'record_level', 'patent_id', 'title',
                      'assignee_normalized', 'url', 'patent_priority_score']].copy()
    for column in ['decision', 'rationale', 'tags', 'watchlist', 'next_action', 'reviewed_at']:
        export[column] = [reviews.get(record_key(row), {}).get(column, False if column == 'watchlist' else '')
                          for _, row in records.iterrows()]
    export['decision'] = export['decision'].replace('', 'Unreviewed')
    export = export[export['watchlist'].astype(bool) if view == 'Watchlist'
                    else export['decision'] != 'Unreviewed']
    st.download_button("Download reviewed records / watchlist (CSV)",
                       export.to_csv(index=False).encode('utf-8-sig'),
                       file_name='patent_reviews.csv', mime='text/csv',
                       disabled=export.empty)
    st.caption("Export reflects the dashboard filters and the selected queue (watchlist or reviewed records).")


def render_detail_table(df):
    """View 5: Detail Table - Searchable with abstract expanders and clickable links."""
    st.header("📋 Patent Details")
    
    # Text search
    search_text = st.text_input("🔍 Search patents by title or assignee", placeholder="e.g., 'Nvidia' or 'safety'")
    
    if search_text:
        search_df = df[
            (df['title'].str.contains(search_text, case=False, na=False)) |
            (df['assignee_normalized'].str.contains(search_text, case=False, na=False))
        ]
    else:
        search_df = df
    
    # Prepare display columns
    display_columns = [
        'patent_id',
        'title',
        'assignee_normalized',
        'jurisdiction',
        'filing_date',
        'grant_date',
        'technology_fields',
        'patent_priority_score',
        'priority_category',
        'industrial_ai_safety_index',
        'functional_role',
        'source',
        'query'
    ]
    
    # Ensure all columns exist
    display_columns = [col for col in display_columns if col in search_df.columns]
    
    # Format dates for display
    display_data = search_df[display_columns].copy()
    for date_col in ['filing_date', 'grant_date']:
        if date_col in display_data.columns:
            display_data[date_col] = pd.to_datetime(display_data[date_col]).dt.strftime('%Y-%m-%d')
    
    # Display patents with expanders for abstracts
    st.subheader(f"Patents ({len(search_df)} results)")
    
    for idx, (_, row) in enumerate(search_df.iterrows()):
        patent_id = row['patent_id']
        title = str(row['title']) if pd.notna(row['title']) else ''
        assignee = row['assignee_normalized']
        
        # Create expander with patent info
        with st.expander(f"🔗 {patent_id} | {title[:60]}...", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Title:** {title}")
                st.write(f"**Assignee:** {assignee}")
                st.write(f"**Jurisdiction:** {row['jurisdiction']}")
                st.write(f"**Filing Date:** {row['filing_date']}")
            with col2:
                st.write(f"**Grant Date:** {row['grant_date']}")
                st.write(f"**Source:** {row['source']}")
                if 'record_level' in row:
                    st.write(f"**Record Level:** {row.get('record_level', 'n/a')}")
                st.write(f"**Query:** {row['query']}")
                if 'patent_priority_score' in row:
                    st.write(f"**Patent Priority Score:** {row['patent_priority_score']}")
                if 'priority_category' in row:
                    st.write(f"**Priority:** {row['priority_category']}")
                if 'functional_role' in row:
                    st.write(f"**Function Role:** {row['functional_role']}")
                
                # Patent link
                if 'url' in search_df.columns and pd.notna(row['url']):
                    link_label = "View Patent Family" if row.get('source') == 'Orbit/FAMPAT' else "View on Google Patents"
                    st.markdown(f"[🔗 {link_label}]({row['url']})")

            if row.get('record_level') == 'Patent Family':
                st.markdown("---")
                st.write(f"**Family Legal Status:** {row.get('family_legal_status', 'n/a')}")
                st.write(f"**Family Legal State:** {row.get('family_legal_state', 'n/a')}")
                st.write(f"**Family Members:** {row.get('family_member_count', 'n/a')}")
                if pd.notna(row.get('family_members')) and str(row.get('family_members')).strip():
                    st.text(str(row.get('family_members')))
                marker_labels = {
                    'marker_person': 'Person',
                    'marker_robot': 'Roboter',
                    'marker_ml_vision': 'ML/Bildauswertung',
                    'marker_stop': 'Stop',
                    'marker_safety': 'Schutz/Sicherheit',
                    'marker_ai': 'KI',
                    'marker_hazard': 'Gefahr',
                    'marker_industrial_machine': 'Industriemaschine',
                    'marker_camera': 'Kamera',
                }
                active_markers = [label for col, label in marker_labels.items() if bool(row.get(col, False))]
                if active_markers:
                    st.write(f"**Markers:** {', '.join(active_markers)}")
                if pd.notna(row.get('legal_status_detail')) and str(row.get('legal_status_detail')).strip():
                    st.write("**Family legal status detail:**")
                    st.code(str(row.get('legal_status_detail')), language=None)

            if 'technology_fields' in row:
                st.markdown("---")
                st.write(f"**Technology Fields:** {row['technology_fields']}")
                score_cols = st.columns(3)
                with score_cols[0]:
                    st.write(f"**KI-Relevanz:** {row.get('ai_relevance_score', 'n/a')}")
                    st.write(f"**Arbeitsschutz:** {row.get('safety_relevance_score', 'n/a')}")
                with score_cols[1]:
                    st.write(f"**Regulierung:** {row.get('regulatory_relevance_score', 'n/a')}")
                    st.write(f"**BAuA-Bezug:** {row.get('baua_fit_score', 'n/a')}")
                with score_cols[2]:
                    st.write(f"**Marktnähe:** {row.get('market_readiness_score', 'n/a')}")
                    st.write(f"**Kritikalität:** {row.get('criticality_score', 'n/a')}")
                st.write(f"**BAuA-Handlungsfeld:** {row.get('baua_action_field', 'n/a')}")
                st.write(f"**Einordnung:** {row.get('functional_role', 'n/a')}")
                st.write(f"**Einordnungsnotiz:** {row.get('functional_role_comment', 'n/a')}")
                st.write(f"**Kommentar:** {row.get('score_comment', 'n/a')}")
            
            # Abstract section
            if 'abstract' in search_df.columns and pd.notna(row['abstract']) and row['abstract'].strip():
                st.markdown("---")
                st.write("**Abstract:**")
                st.write(row['abstract'])
    
    # Export functionality
    st.markdown("---")
    st.subheader("📥 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # CSV export
        csv_data = search_df.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="⬇️ Download as CSV",
            data=csv_data,
            file_name=f"patents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        st.caption(f"Showing {len(search_df)} of {len(df)} patents")


def main():
    """Main application entry point."""
    # Load data
    df = load_data(data_signature=_data_file_signature())
    
    if df.empty:
        st.error("No data available. Please check the data file.")
        return

    try:
        init_reviews()
        reviews = load_reviews()
    except (OSError, sqlite3.Error) as exc:
        st.error(f"Cannot open local review database: {exc}")
        return
    
    # Render header
    render_header()
    
    # Apply filters and get filtered data
    filtered_df, applied_filters = apply_filters(df)
    
    # Show filter summary
    if applied_filters['sources'] != list(df['source'].unique()):
        st.sidebar.info(f"Filtered: {len(filtered_df)} of {len(df)} patents")
    
    # Tab navigation
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "📈 Trends",
        "📝 Review Queue",
        "🏢 Assignees",
        "🌍 Jurisdiction",
        "🔎 Queries",
        "⚖️ Regulation & BAuA",
        "👪 Family Intelligence",
        "🏆 Competitive Intel",
        "📝 Abstract Intelligence",
        "📋 Details"
    ])
    
    with tab1:
        render_overview_metrics(filtered_df)
        render_trend_dashboard(filtered_df)

    with tab2:
        render_review_queue(filtered_df, reviews)

    with tab3:
        render_assignee_landscape(filtered_df)

    with tab4:
        render_jurisdiction_analysis(filtered_df)

    with tab5:
        render_query_performance(filtered_df)

    with tab6:
        render_regulatory_relevance(filtered_df)

    with tab7:
        render_family_intelligence(filtered_df)

    with tab8:
        render_competitive_intel(filtered_df)

    with tab9:
        render_abstract_intelligence(filtered_df)

    with tab10:
        render_detail_table(filtered_df)
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 0.9em;'>
            Patent Trends Dashboard | Data Sources: Google Patents, Orbit/FAMPAT | BAuA Research
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

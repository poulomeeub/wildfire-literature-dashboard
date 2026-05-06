import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================================
# Wildfire Literature Dashboard
# =========================================================
# Run:
#   python -m streamlit run wildfire_bib_dashboard.py
# Keep this .py file in the same folder as:
#   wildfire_bib_247_title_summary_ai_qc_table(2).csv
# =========================================================

st.set_page_config(
    page_title="Wildfire Literature Dashboard",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_CSV = "wildfire_bib_247_title_summary_ai_qc_table(2).csv"

@st.cache_data(show_spinner=False)
def load_data(uploaded_file=None):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        csv_path = Path(__file__).parent / DEFAULT_CSV
        if not csv_path.exists():
            st.error(f"CSV not found: {csv_path}\n\nUpload the CSV from the sidebar or place it beside this script.")
            st.stop()
        df = pd.read_csv(csv_path)

    df.columns = [str(c).strip() for c in df.columns]

    for col in ["SM", "CISF", "E", "AIQC"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)
        df[col + "_flag"] = df[col].str.contains(r"checkmark|✓|yes|true|1", flags=re.I, regex=True)

    for col in ["key", "title", "summary"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    else:
        df["year"] = pd.NA

    df["AI_QC_Status"] = df["AIQC_flag"].map({True: "AI/QC", False: "Non AI/QC"})
    df["Study_Type_Count"] = df[["SM_flag", "CISF_flag", "E_flag"]].sum(axis=1)
    df["Category"] = "Other"
    df.loc[df["SM_flag"], "Category"] = "Spread / Simulation Model"
    df.loc[df["CISF_flag"], "Category"] = "Critical Infrastructure / Cascading Failure"
    df.loc[df["E_flag"], "Category"] = "Evacuation / Emergency Response"
    df.loc[df["AIQC_flag"], "Category"] = "AI & Quantum Computing"

    return df


def keyword_counts(df, text_col="title", top_n=20):
    stop = {
        "the", "and", "for", "with", "from", "that", "this", "into", "using", "based", "after", "during",
        "fire", "wildfire", "wildfires", "study", "analysis", "model", "models", "risk", "case", "approach",
        "california", "data", "towards", "toward", "via", "new", "one", "years", "deadly", "history"
    }
    words = []
    for text in df[text_col].dropna().astype(str):
        words.extend(re.findall(r"[A-Za-z]{4,}", text.lower()))
    counts = pd.Series(words).value_counts()
    counts = counts[~counts.index.isin(stop)].head(top_n).reset_index()
    counts.columns = ["keyword", "count"]
    return counts


st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #160b05 0%, #2c1207 35%, #5b1f0b 100%);
        color: #fff;
    }
    [data-testid="stSidebar"] {
        background: rgba(20, 12, 9, 0.96);
    }
    .main-card {
        padding: 1.1rem 1.3rem;
        border-radius: 18px;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.14);
        box-shadow: 0 8px 28px rgba(0,0,0,0.25);
    }
    .metric-card {
        padding: 1rem;
        border-radius: 16px;
        background: rgba(255, 244, 235, 0.11);
        border: 1px solid rgba(255,255,255,0.13);
        text-align: center;
    }
    .metric-value {font-size: 2.1rem; font-weight: 800; color: #ffdfbd;}
    .metric-label {font-size: 0.9rem; color: #f4d6c3;}
    h1, h2, h3 {color: #fff7ef;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔥 Wildfire Literature Review Dashboard")
st.caption("Interactive dashboard for the 247-paper BibTeX/title/summary AI-QC table")

with st.sidebar:
    st.header("Dashboard Controls")
    uploaded = st.file_uploader("Upload updated CSV", type=["csv"])
    df = load_data(uploaded)

    years = sorted([int(y) for y in df["year"].dropna().unique()])
    if years:
        year_range = st.slider("Year range", min(years), max(years), (min(years), max(years)))
    else:
        year_range = None

    category_options = ["Spread / Simulation Model", "Critical Infrastructure / Cascading Failure", "Evacuation / Emergency Response", "AI & Quantum Computing", "Other"]
    selected_categories = st.multiselect("Categories", category_options, default=category_options)
    ai_qc_filter = st.selectbox("AI/QC filter", ["All", "AI/QC only", "Non AI/QC only"])
    search_text = st.text_input("Search title, key, or summary")

filtered = df.copy()
if year_range is not None:
    filtered = filtered[(filtered["year"].isna()) | ((filtered["year"] >= year_range[0]) & (filtered["year"] <= year_range[1]))]
if selected_categories:
    filtered = filtered[filtered["Category"].isin(selected_categories)]
if ai_qc_filter == "AI/QC only":
    filtered = filtered[filtered["AIQC_flag"]]
elif ai_qc_filter == "Non AI/QC only":
    filtered = filtered[~filtered["AIQC_flag"]]
if search_text.strip():
    q = search_text.strip().lower()
    mask = (
        filtered["title"].str.lower().str.contains(q, na=False)
        | filtered["key"].str.lower().str.contains(q, na=False)
        | filtered["summary"].str.lower().str.contains(q, na=False)
    )
    filtered = filtered[mask]

# KPIs
c1, c2, c3, c4, c5 = st.columns(5)
metrics = [
    ("Papers", len(filtered)),
    ("AI/QC", int(filtered["AIQC_flag"].sum())),
    ("SM", int(filtered["SM_flag"].sum())),
    ("CISF", int(filtered["CISF_flag"].sum())),
    ("Evacuation", int(filtered["E_flag"].sum())),
]
for col, (label, value) in zip([c1, c2, c3, c4, c5], metrics):
    with col:
        st.markdown(f"<div class='metric-card'><div class='metric-value'>{value}</div><div class='metric-label'>{label}</div></div>", unsafe_allow_html=True)

st.write("")

left, right = st.columns([1.25, 1])
with left:
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    st.subheader("Papers by Year")
    year_counts = filtered.dropna(subset=["year"]).groupby("year").size().reset_index(name="papers")
    if not year_counts.empty:
        fig = px.bar(year_counts, x="year", y="papers", text="papers", title=None)
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No year data available for this filter.")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    st.subheader("Category Coverage")
    cat_data = pd.DataFrame({
        "Category": ["SM", "CISF", "Evacuation", "AI/QC"],
        "Count": [filtered["SM_flag"].sum(), filtered["CISF_flag"].sum(), filtered["E_flag"].sum(), filtered["AIQC_flag"].sum()],
    })
    fig = px.pie(cat_data, names="Category", values="Count", hole=0.45)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", font_color="white")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

left2, right2 = st.columns([1, 1])
with left2:
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    st.subheader("AI/QC vs Non-AI/QC by Year")
    ai_year = filtered.dropna(subset=["year"]).groupby(["year", "AI_QC_Status"]).size().reset_index(name="papers")
    if not ai_year.empty:
        fig = px.bar(ai_year, x="year", y="papers", color="AI_QC_Status", barmode="group")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No AI/QC-year data available.")
    st.markdown("</div>", unsafe_allow_html=True)

with right2:
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    st.subheader("Top Title Keywords")
    kw = keyword_counts(filtered, "title", 18)
    if not kw.empty:
        fig = px.bar(kw.sort_values("count"), x="count", y="keyword", orientation="h")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No keywords found.")
    st.markdown("</div>", unsafe_allow_html=True)

st.subheader("Filtered Literature Table")
show_cols = [c for c in ["#", "key", "title", "year", "summary", "SM", "CISF", "E", "AIQC", "Category"] if c in filtered.columns]
st.dataframe(filtered[show_cols], use_container_width=True, height=460)

csv_download = filtered[show_cols].to_csv(index=False).encode("utf-8")
st.download_button("Download filtered table as CSV", data=csv_download, file_name="filtered_wildfire_literature.csv", mime="text/csv")

with st.expander("About column labels"):
    st.markdown(
        """
        - **SM**: Spread / Simulation Model studies  
        - **CISF**: Critical Infrastructure / Cascading Failure studies  
        - **E**: Evacuation / Emergency Response studies  
        - **AIQC**: Artificial Intelligence / Quantum Computing studies
        """
    )

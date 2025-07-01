"""
Streamlit dashboard for WRPF UK Records Database
===============================================
Run with:
    streamlit run records_dashboard.py

Files expected in the same directory (or adjust paths):
* **Records Master Sheet.csv** – data source
* **wrpf_logo.png**            – logo for branding banner

What’s inside
-------------
* Sidebar filters (Division, Testing Status, Discipline, etc.)
* Landing screen shows left-aligned logo + title; table appears only after filters are applied
* Index column hidden; “Location” renamed to “Event”
* Streamlit theme forced to dark mode via inline CSS (works on Cloud too)
"""

import pandas as pd
import streamlit as st
from pathlib import Path

CSV_PATH = Path(__file__).with_name("Records Master Sheet.csv")
LOGO_PATH = Path(__file__).with_name("wrpf_logo.png")

# ----------------------------------------------------
# Simple dark-mode override + text styling
# ----------------------------------------------------

DARK_CSS = """
<style>
body, .stApp, .block-container {
    background-color: #0e1117;
    color: #ffffff !important;
}

/* Force black for key headings */
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stCaption {
    color: #000000 !important;
}

/* Table text */
[data-testid="stDataFrame"] div {
    color: #ffffff !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #111417;
    color: #ffffff !important;
}
</style>
"""

# Lift mapping
LIFT_MAP   = {"S": "Squat", "B": "Bench", "D": "Deadlift", "T": "Total", "Total": "Total"}
LIFT_ORDER = ["Squat", "Bench", "Deadlift", "Total"]
INVALID_WEIGHT_CLASSES = {"736", "737", "738", "739", "cell"}

@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df = df[df["Full Name"].notna() & df["Weight"].notna()]
    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    df["Class"]  = df["Class"].astype(str).str.strip()
    df = df[~df["Class"].isin(INVALID_WEIGHT_CLASSES)]

    # Division cleanup & testing flag
    df["Division_raw"]  = df["Division"].str.strip()
    df["Division_base"] = df["Division_raw"].str.replace(r"DT$", "", regex=True)
    df["Testing"]       = df["Division_raw"].str.endswith("DT").map({True: "Tested", False: "Untested"})

    df["

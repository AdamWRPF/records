"""
Streamlit dashboard for WRPF UK Records Database
===============================================
Run:
    streamlit run records_dashboard.py

Files required (same folder):
* Records Master Sheet.csv  – data source
* wrpf_logo.png            – logo (optional but recommended)

Navigation
----------
* **Home** – searchable records table (default)
* **Insights** – quick federation analytics:
    1. Records Growth
    3. Age-division vs. Performance
    4. Gender Split
    5. Recent Record Turnover (last 6 months)

Toolbar links (top): Memberships, Results, Events, Livestreams, Insights
"""

import pandas as pd
import altair as alt
import streamlit as st
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlencode

CSV_PATH  = Path(__file__).with_name("Records Master Sheet.csv")
LOGO_PATH = Path(__file__).with_name("wrpf_logo.png")

# Lift mapping & display order ------------------------------------------------
LIFT_MAP   = {"S": "Squat", "B": "Bench", "D": "Deadlift", "T": "Total", "Total": "Total"}
LIFT_ORDER = ["Squat", "Bench", "Deadlift", "Total"]
INVALID_WEIGHT_CLASSES = {"736", "737", "738", "739", "cell"}

# Desired division dropdown order --------------------------------------------
DIVISION_ORDER = [
    "T14-15", "T16-17", "T18-19",
    "Junior", "Opens",
    "M40-49", "M50-59", "M60-69", "M70-79",
]

# -----------------------------------------------------------------------------
# Data loading & caching
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df = df[df["Full Name"].notna() & df["Weight"].notna()]
    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    df["Class"]  = df["Class"].astype(str).str.strip()
    df = df[~df["Class"].isin(INVALID_WEIGHT_CLASSES)]

    # Division & testing
    df["Division_raw"]  = df["Division"].str.strip()
    df["Division_base"] = df["Division_raw"].str.replace(r"DT$", "", regex=True)
    df["Testing"]       = df["Division_raw"].str.endswith("DT").map({True: "Tested", False: "Untested"})

    # Lift labels
    df["Lift"] = df["Lift"].replace(LIFT_MAP).fillna(df["Lift"])

    # Parse dates
    df["Date_parsed"] = pd.to_datetime(df["Date"], errors="coerce")

    for col in ["Record Type", "Lift", "Record Name"]:
        df[col] = df[col].fillna("")
    return df

# -----------------------------------------------------------------------------
# Sidebar filters (home page only)
# -----------------------------------------------------------------------------

def sidebar_filters(df: pd.DataFrame):
    st.sidebar.header("Filter Records")
    sel = {}

    sel["discipline"] = st.sidebar.selectbox("Discipline", ["All", "Full Power", "Single Lifts"])

    def box(label, opts):
        return st.sidebar.selectbox(label, ["All"] + opts)

    sel["sex"] = box("Sex", sorted(df["Sex"].dropna().unique()))

    available_divs = list(dict.fromkeys(df["Division_base"].unique()))
    ordered_divs   = [d for d in DIVISION_ORDER if d in available_divs] + [d for d in available_divs if d not in DIVISION_ORDER]
    sel["division"] = box("Division", ordered_divs)

    sel["testing_status"] = box("Testing Status", ["Tested", "Untested"])
    sel["equipment"]      = box("Equipment", sorted(df["Equipment"].dropna().unique()))
    weight_opts = sorted(df["Class"].unique(), key=lambda x: (pd.to_numeric(x, errors="coerce"), x))
    sel["weight_class"]   = box("Weight Class", weight_opts)
    sel["search"]         = st.sidebar.text_input("Search by name or record")

    # Filtering -----------------------------------------------------------
    filt = df.copy()
    if sel["discipline"] == "Full Power":
        filt = filt[~filt["Record Type"].str.contains("Single", case=False, na=False)]
    elif sel["discipline"] == "Single Lifts":
        mask = filt["Record Type"].str.contains("Single|Bench Only|Deadlift Only", case=False, na=False)
        filt = filt[mask & filt["Lift"].isin(["Bench", "Deadlift"])]

    if sel["sex"]            != "All": filt = filt[filt["Sex"] == sel["sex"]]
    if sel["division"]       != "All": filt = filt[filt["Division_base"] == sel["division"]]
    if sel["testing_status"] != "All": filt = filt[filt["Testing"] == sel["testing_status"]]
    if sel["equipment"]      != "All": filt = filt[filt["Equipment"] == sel["equipment"]]
    if sel["weight_class"]   != "All": filt = filt[filt["Class"] == sel["weight_class"]]

    if sel["search"]:
        txt = sel["search"]
        filt = filt[filt["Full Name"].str.contains(txt, case=False, na=False) |
                    filt["Record Name"].str.contains(txt, case=False, na=False)]

    return filt, sel

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def best_per_class_and_lift(df: pd.DataFrame) -> pd.DataFrame:
    best = (
        df.sort_values("Weight", ascending=False)
          .drop_duplicates(subset=["Class", "Lift"])
          .assign(
              _class_num=lambda d: pd.to_numeric(d["Class"], errors="coerce"),
              _lift_order=lambda d: d["Lift"].apply(lambda x: LIFT_ORDER.index(x) if x in LIFT_ORDER else 99)
          )
          .sort_values(["_class_num", "Class", "_lift_order"])
          .drop(columns=["_class_num", "_lift_order"])
    )
    return best

# -----------------------------------------------------------------------------
# Insights page visuals
# -----------------------------------------------------------------------------

def render_insights(df: pd.DataFrame):
    st.header("Federation Insights")

    # 1. Records Growth ----------------------------------------------------
    st.subheader("Records Growth by Year")
    growth = df.dropna(subset=["Date_parsed"]).copy()
    growth["Year"] = growth["Date_parsed"].dt.year
    annual = growth.groupby("Year").size().reset_index(name="Records")
    chart1 = alt.Chart(annual).mark_line(point=True).encode(
        x="Year:O", y="Records:Q", tooltip=["Year", "Records"]
    )
    st.altair_chart(chart1, use_container_width=True)

    # 3. Age vs Performance -----------------------------------------------
    st.subheader("Age Division vs. Record Weight")
    age_perf = df.copy()
    age_perf = age_perf[age_perf["Division_base"].isin(DIVISION_ORDER)]
    order_age = DIVISION_ORDER
    chart2 = alt.Chart(age_perf).mark_circle(size=60, opacity=0.5).encode(
        x=alt.X("Division_base:N", sort=order_age, title="Division"),
        y=alt.Y("Weight:Q", title="Record Weight (kg)"),
        color="Lift:N",
        tooltip=["Full Name", "Lift", "Weight", "Division_base", "Date"]
    )
    st.altair_chart(chart2, use_container_width=True)

    # 4. Gender Split ------------------------------------------------------
    st.subheader("Gender Split of Records")
    gender_counts = df.groupby("Sex").size().reset_index(name="Count")
    chart3 = alt.Chart(gender_counts).mark_bar().encode(
        x="Sex:N", y="Count:Q", tooltip=["Sex", "Count"], color="Sex:N"
    )
    st.altair_chart(chart3, use_container_width=True)

    # 5. Recent Record Turnover -------------------------------------------
    st.subheader("Records Broken in the Last 6 Months")
    cutoff = datetime.utcnow() - timedelta(days=182)
    recent = df[df["Date_parsed"] >= cutoff]
    if recent.empty:
        st.write("No records broken in the last 6 months.")
    else:
        st.dataframe(
            recent[["Date", "Full Name", "Division_base", "Class", "Lift", "Weight"]]
                .rename(columns={"Full Name": "Name", "Division_base": "Division"})
                .sort_values("Date_parsed", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="WRPF UK Records Database", layout="wide")

    # Query param routing --------------------------------------------------
    page = st.experimental_get_query_params().get("page", ["home"])[0]

    # Toolbar --------------------------------------------------------------
    def nav_link(label, target):
        qs = "" if target == "home" else "?" + urlencode({"page": target})
        return f"[**{label}**]({qs})"

    toolbar_cols = st.columns(5)
    toolbar_items = [
        ("Memberships", "https://www.wrpf.uk/memberships").

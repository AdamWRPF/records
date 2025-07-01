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
* Top toolbar links: Memberships, Results, Events, Livestreams
* Sidebar filters (Division, Testing Status, Discipline, etc.)
* Landing screen shows left-aligned logo + title; table appears only after filters are applied
* Index column hidden; “Location” renamed to “Event”
"""

import pandas as pd
import streamlit as st
from pathlib import Path

CSV_PATH  = Path(__file__).with_name("Records Master Sheet.csv")
LOGO_PATH = Path(__file__).with_name("wrpf_logo.png")

# Mapping raw lift codes → readable labels
LIFT_MAP   = {"S": "Squat", "B": "Bench", "D": "Deadlift", "T": "Total", "Total": "Total"}
LIFT_ORDER = ["Squat", "Bench", "Deadlift", "Total"]
INVALID_WEIGHT_CLASSES = {"736", "737", "738", "739", "cell"}

# -------------------------------------------------------------------------
# Data utilities
# -------------------------------------------------------------------------

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

    # Lift labels
    df["Lift"] = df["Lift"].replace(LIFT_MAP).fillna(df["Lift"])

    for col in ["Record Type", "Lift", "Record Name"]:
        df[col] = df[col].fillna("")
    return df

# -------------------------------------------------------------------------
# Sidebar filters
# -------------------------------------------------------------------------

def sidebar_filters(df: pd.DataFrame):
    st.sidebar.header("Filter Records")
    sel = {}

    sel["discipline"] = st.sidebar.selectbox("Discipline", ["All", "Full Power", "Single Lifts"])

    def box(label, opts):
        opts_sorted = sorted(opts)
        return st.sidebar.selectbox(label, ["All"] + opts_sorted)

    sel["sex"]            = box("Sex", df["Sex"].dropna().unique())
    sel["division"]       = box("Division", df["Division_base"].unique())
    sel["testing_status"] = box("Testing Status", ["Tested", "Untested"])
    sel["equipment"]      = box("Equipment", df["Equipment"].dropna().unique())
    weight_opts           = sorted(df["Class"].unique(), key=lambda x: (pd.to_numeric(x, errors="coerce"), x))
    sel["weight_class"]   = box("Weight Class", weight_opts)
    sel["search"]         = st.sidebar.text_input("Search by name or record")

    # Apply filters -------------------------------------------------------
    filt = df.copy()
    if sel["discipline"] == "Full Power":
        filt = filt[~filt["Record Type"].str.contains("Single", case=False, na=False)]
    elif sel["discipline"] == "Single Lifts":
        single = filt["Record Type"].str.contains("Single|Bench Only|Deadlift Only", case=False, na=False)
        filt   = filt[single & filt["Lift"].isin(["Bench", "Deadlift"])]

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

# -------------------------------------------------------------------------
# Helper: best record per (class, lift)
# -------------------------------------------------------------------------

def best_per_class_and_lift(df: pd.DataFrame) -> pd.DataFrame:
    ranked = df.sort_values("Weight", ascending=False)
    best   = ranked.drop_duplicates(subset=["Class", "Lift"])
    best   = best.copy()
    best["_class_num"] = pd.to_numeric(best["Class"], errors="coerce")
    best["_lift_order"] = best["Lift"].apply(lambda x: LIFT_ORDER.index(x) if x in LIFT_ORDER else 99)
    return best.sort_values(["_class_num", "Class", "_lift_order"]).drop(columns=["_class_num", "_lift_order"])

# -------------------------------------------------------------------------
# Main app
# -------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="WRPF UK Records Database", layout="wide")

    # Toolbar at very top
    toolbar_links = {
        "Memberships": "https://www.wrpf.uk/memberships",
        "Results":     "https://www.wrpf.uk/results",
        "Events":      "https://www.wrpf.uk/events",
        "Livestreams": "https://www.wrpf.uk/live",
    }
    top_cols = st.columns(len(toolbar_links))
    for col, (label, url) in zip(top_cols, toolbar_links.items()):
        col.markdown(f"[**{label}**]({url})", unsafe_allow_html=True)

    # Branding banner under toolbar
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=140)
    st.markdown("## **WRPF UK Records Database**")
    st.caption("Where Strength Meets Opportunity")

    df = load_data(CSV_PATH)
    filtered, sel = sidebar_filters(df)

    defaults = {k: "All" for k in ["discipline", "sex", "division", "testing_status", "equipment", "weight_class"]}
    defaults["search"] = ""
    filters_applied = any(sel[k] != defaults[k] for k in defaults)

    if filters_applied and not filtered.empty:
        st.subheader("Top Record in Each Weight Class & Lift")
        best = best_per_class_and_lift(filtered)
        st.dataframe(
            best[["Class", "Lift", "Weight", "Full Name", "Division_base", "Testing", "Date", "Location"]]
            .rename(columns={"Full Name": "Name", "Division_base": "Division", "Location": "Event"}),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("👈 Use the menu on the left to pick filters and see records.")

if __name__ == "__main__":
    main()

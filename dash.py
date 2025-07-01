"""
Streamlit dashboard for WRPF UK Records Database
===============================================

Run with:
    streamlit run records_dashboard.py

Place **Records Master Sheet.csv** in the same directory (or adjust `CSV_PATH`).

Key features
------------
* **Discipline** filter – All, Full Power, Single Lifts.
* **Division** filter now shows *clean* categories (e.g. Junior, Open, Masters). Variants ending in **DT** are merged with their non‑DT counterpart.
* **Testing Status** filter – All, Tested (divisions ending with **DT**), Untested (all others).
* Additional filters: Sex, Equipment, Weight Class, free‑text search.
* Table lists the heaviest record for every (weight class, lift) combination that survives filters.
* Rows with obvious artefacts in the Weight Class column (736–739, "cell") are removed.
"""

import pandas as pd
import streamlit as st
from pathlib import Path

CSV_PATH = Path(__file__).with_name("Records Master Sheet.csv")

# Human‑readable lift names
LIFT_MAP = {
    "S": "Squat",
    "B": "Bench",
    "D": "Deadlift",
    "T": "Total",
    "Total": "Total",
}
LIFT_ORDER = ["Squat", "Bench", "Deadlift", "Total"]

INVALID_WEIGHT_CLASSES = {"736", "737", "738", "739", "cell"}

# -------------------------------------------------------------------------
# Data loading & normalisation
# -------------------------------------------------------------------------

@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    # Basic cleaning
    df = df[df["Full Name"].notna() & df["Weight"].notna()]
    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    df["Class"] = df["Class"].astype(str).str.strip()

    # Remove artefact rows
    df = df[~df["Class"].isin(INVALID_WEIGHT_CLASSES)]

    # Normalise division
    df["Division_raw"] = df["Division"].str.strip()
    df["Division_base"] = df["Division_raw"].str.replace(r"DT$", "", regex=True)
    df["Testing"] = df["Division_raw"].str.endswith("DT").map({True: "Tested", False: "Untested"})

    # Map lifts to labels
    df["Lift"] = df["Lift"].replace(LIFT_MAP).fillna(df["Lift"])

    # Ensure string columns safe for .str.contains
    for col in ["Record Type", "Lift", "Record Name"]:
        df[col] = df[col].fillna("")

    return df

# -------------------------------------------------------------------------
# Sidebar filters
# -------------------------------------------------------------------------

def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filter Records")

    discipline = st.sidebar.selectbox("Discipline", ["All", "Full Power", "Single Lifts"])

    def selectbox(label: str, options: list):
        return st.sidebar.selectbox(label, ["All"] + options)

    # Build options lists
    division_opts = sorted(df["Division_base"].unique())
    sex_opts = sorted(df["Sex"].dropna().unique())
    equip_opts = sorted(df["Equipment"].dropna().unique())
    weight_opts = sorted(df["Class"].unique(), key=lambda x: (pd.to_numeric(x, errors="coerce"), x))
    testing_opts = ["Tested", "Untested"]

    sex = selectbox("Sex", sex_opts)
    division = selectbox("Division", division_opts)
    testing_status = selectbox("Testing Status", testing_opts)
    equipment = selectbox("Equipment", equip_opts)
    weight_class = selectbox("Weight Class", weight_opts)
    search = st.sidebar.text_input("Search by name or record")

    filt = df.copy()

    # Discipline filtering
    if discipline == "Full Power":
        filt = filt[~filt["Record Type"].str.contains("Single", case=False, na=False)]
    elif discipline == "Single Lifts":
        mask_single = filt["Record Type"].str.contains("Single|Bench Only|Deadlift Only", case=False, na=False)
        filt = filt[mask_single & filt["Lift"].isin(["Bench", "Deadlift"])]

    # Attribute filters
    if sex != "All":
        filt = filt[filt["Sex"] == sex]
    if division != "All":
        filt = filt[filt["Division_base"] == division]
    if testing_status != "All":
        filt = filt[filt["Testing"] == testing_status]
    if equipment != "All":
        filt = filt[filt["Equipment"] == equipment]
    if weight_class != "All":
        filt = filt[filt["Class"] == weight_class]

    # Free‑text search
    if search:
        search_mask = (
            filt["Full Name"].str.contains(search, case=False, na=False) |
            filt["Record Name"].str.contains(search, case=False, na=False)
        )
        filt = filt[search_mask]

    return filt

# -------------------------------------------------------------------------
# Helpers: choose best record per (class, lift)
# -------------------------------------------------------------------------

def best_per_class_and_lift(df: pd.DataFrame) -> pd.DataFrame:
    ranked = df.sort_values("Weight", ascending=False)
    best = ranked.drop_duplicates(subset=["Class", "Lift"])

    best = best.copy()
    best["_class_num"] = pd.to_numeric(best["Class"], errors="coerce")
    best["_lift_order"] = best["Lift"].apply(lambda x: LIFT_ORDER.index(x) if x in LIFT_ORDER else 99)
    best = best.sort_values(["_class_num", "Class", "_lift_order"]).drop(columns=["_class_num", "_lift_order"])
    return best

# -------------------------------------------------------------------------
# Main app
# -------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="WRPF UK Records Database", layout="wide")
    st.title("WRPF UK Records Database")
    st.caption("Data source: Records Master Sheet.csv")

    df = load_data(CSV_PATH)
    filtered = sidebar_filters(df)

    st.subheader("Top Record in Each Weight Class & Lift")
    best = best_per_class_and_lift(filtered)

    if best.empty:
        st.info("No records match the current filters.")
    else:
        st.dataframe(
            best[["Class", "Lift", "Weight", "Full Name", "Division_base", "Testing", "Date", "Location"]]
            .rename(columns={"Full Name": "Name", "Division_base": "Division"}),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()

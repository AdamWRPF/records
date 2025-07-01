"""
Streamlit dashboard for WRPF UK Records Database
===============================================

Run with:
    streamlit run records_dashboard.py

Place **Records Master Sheet.csv** in the same directory (or adjust `CSV_PATH`).

Key points
----------
* **Discipline** controls which lifts appear:
  * **Full Power** – shows Squat, Bench, Deadlift and Total records (rows whose Record Type does *not* mention single-lift events).
  * **Single Lifts** – shows Bench & Deadlift rows tagged as single-lift (Record Type contains "Single", "Bench Only", or "Deadlift Only").
  * **All** – no additional discipline filtering.
* Other sidebar filters: Sex, Division, Equipment, Weight Class, free-text search.
* Table lists the heaviest record for every **(weight class, lift)** that survives the filters.
* No separate “Lift” filter; the Discipline setting suffices.
* Obvious spreadsheet artefacts in the Class column (736–739, "cell") are ignored.
"""

import pandas as pd
import streamlit as st
from pathlib import Path

CSV_PATH = Path(__file__).with_name("Records Master Sheet.csv")

# Mapping from dataset codes → human-readable labels
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
# Data loading & cleaning
# -------------------------------------------------------------------------

def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    # Basic sanity checks
    df = df[df["Full Name"].notna() & df["Weight"].notna()]
    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    df["Class"] = df["Class"].astype(str).str.strip()

    # Remove artefacts
    df = df[~df["Class"].isin(INVALID_WEIGHT_CLASSES)]

    # Map lift codes to labels
    df["Lift"] = df["Lift"].replace(LIFT_MAP).fillna(df["Lift"])

    # Prevent NaN issues in string searches
    for col in ["Record Type", "Lift", "Record Name"]:
        df[col] = df[col].fillna("")

    return df


# -------------------------------------------------------------------------
# Sidebar filters
# -------------------------------------------------------------------------

def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filter Records")

    discipline = st.sidebar.selectbox("Discipline", ["All", "Full Power", "Single Lifts"])

    def selectbox(label: str, column: str):
        options = ["All"] + sorted(df[column].dropna().unique())
        return st.sidebar.selectbox(label, options)

    sex = selectbox("Sex", "Sex")
    division = selectbox("Division", "Division")
    equipment = selectbox("Equipment", "Equipment")
    weight_class = selectbox("Weight Class", "Class")
    search = st.sidebar.text_input("Search by name or record")

    filt = df.copy()

    # --- Discipline logic -------------------------------------------------
    if discipline == "Full Power":
        filt = filt[~filt["Record Type"].str.contains("Single", case=False, na=False)]
        # Keeps Squat, Bench, Deadlift, Total
    elif discipline == "Single Lifts":
        single_mask = filt["Record Type"].str.contains("Single|Bench Only|Deadlift Only", case=False, na=False)
        filt = filt[single_mask & filt["Lift"].isin(["Bench", "Deadlift"])]

    # --- Attribute filters ------------------------------------------------
    if sex != "All":
        filt = filt[filt["Sex"] == sex]
    if division != "All":
        filt = filt[filt["Division"] == division]
    if equipment != "All":
        filt = filt[filt["Equipment"] == equipment]
    if weight_class != "All":
        filt = filt[filt["Class"] == weight_class]

    # --- Text search ------------------------------------------------------
    if search:
        mask = (
            filt["Full Name"].str.contains(search, case=False, na=False) |
            filt["Record Name"].str.contains(search, case=False, na=False)
        )
        filt = filt[mask]

    return filt


# -------------------------------------------------------------------------
# Record selection helpers
# -------------------------------------------------------------------------

def best_per_class_and_lift(df: pd.DataFrame) -> pd.DataFrame:
    ranked = df.sort_values("Weight", ascending=False)
    best = ranked.drop_duplicates(subset=["Class", "Lift"])

    # Order weight classes numerically when possible, then lift order
    best = best.copy()
    best["_class_num"] = pd.to_numeric(best["Class"], errors="coerce")
    best["_lift_order"] = best["Lift"].apply(lambda x: LIFT_ORDER.index(x) if x in LIFT_ORDER else 99)
    best = best.sort_values(["_class_num", "Class", "_lift_order"]).drop(columns=["_class_num", "_lift_order"])
    return best


# -------------------------------------------------------------------------
# App
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
            best[["Class", "Lift", "Weight", "Full Name", "Division", "Date", "Location"]]
            .rename(columns={"Full Name": "Name"}),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
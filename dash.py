import pandas as pd
import streamlit as st
from pathlib import Path

CSV_PATH = Path(__file__).with_name("Records Master Sheet.csv")
LOGO_PATH = Path(__file__).with_name("wrpf_logo.png")  # add your logo file here

LIFT_MAP = {"S": "Squat", "B": "Bench", "D": "Deadlift", "T": "Total", "Total": "Total"}
LIFT_ORDER = ["Squat", "Bench", "Deadlift", "Total"]
INVALID_WEIGHT_CLASSES = {"736", "737", "738", "739", "cell"}

@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df = df[df["Full Name"].notna() & df["Weight"].notna()]
    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    df["Class"] = df["Class"].astype(str).str.strip()
    df = df[~df["Class"].isin(INVALID_WEIGHT_CLASSES)]
    df["Division_raw"] = df["Division"].str.strip()
    df["Division_base"] = df["Division_raw"].str.replace(r"DT$", "", regex=True)
    df["Testing"] = df["Division_raw"].str.endswith("DT").map({True: "Tested", False: "Untested"})
    df["Lift"] = df["Lift"].replace(LIFT_MAP).fillna(df["Lift"])
    for col in ["Record Type", "Lift", "Record Name"]:
        df[col] = df[col].fillna("")
    return df

def sidebar_filters(df: pd.DataFrame):
    st.sidebar.header("Filter Records")
    selections = {}
    selections["discipline"] = st.sidebar.selectbox("Discipline", ["All", "Full Power", "Single Lifts"])
    def box(label, opts):
        return st.sidebar.selectbox(label, ["All"] + opts)
    selections["sex"] = box("Sex", sorted(df["Sex"].dropna().unique()))
    selections["division"] = box("Division", sorted(df["Division_base"].unique()))
    selections["testing_status"] = box("Testing Status", ["Tested", "Untested"])
    selections["equipment"] = box("Equipment", sorted(df["Equipment"].dropna().unique()))
    weight_opts = sorted(df["Class"].unique(), key=lambda x: (pd.to_numeric(x, errors="coerce"), x))
    selections["weight_class"] = box("Weight Class", weight_opts)
    selections["search"] = st.sidebar.text_input("Search by name or record")

    filt = df.copy()
    if selections["discipline"] == "Full Power":
        filt = filt[~filt["Record Type"].str.contains("Single", case=False, na=False)]
    elif selections["discipline"] == "Single Lifts":
        mask_single = filt["Record Type"].str.contains("Single|Bench Only|Deadlift Only", case=False, na=False)
        filt = filt[mask_single & filt["Lift"].isin(["Bench", "Deadlift"])]

    if selections["sex"] != "All":
        filt = filt[filt["Sex"] == selections["sex"]]
    if selections["division"] != "All":
        filt = filt[filt["Division_base"] == selections["division"]]
    if selections["testing_status"] != "All":
        filt = filt[filt["Testing"] == selections["testing_status"]]
    if selections["equipment"] != "All":
        filt = filt[filt["Equipment"] == selections["equipment"]]
    if selections["weight_class"] != "All":
        filt = filt[filt["Class"] == selections["weight_class"]]

    if selections["search"]:
        txt = selections["search"]
        m = filt["Full Name"].str.contains(txt, case=False, na=False) | filt["Record Name"].str.contains(txt, case=False, na=False)
        filt = filt[m]

    return filt, selections

def best_per_class_and_lift(df: pd.DataFrame) -> pd.DataFrame:
    ranked = df.sort_values("Weight", ascending=False)
    best = ranked.drop_duplicates(subset=["Class", "Lift"])
    best = best.copy()
    best["_class_num"] = pd.to_numeric(best["Class"], errors="coerce")
    best["_lift_order"] = best["Lift"].apply(lambda x: LIFT_ORDER.index(x) if x in LIFT_ORDER else 99)
    best = best.sort_values(["_class_num", "Class", "_lift_order"]).drop(columns=["_class_num", "_lift_order"])
    return best

def main():
    st.set_page_config(page_title="WRPF UK Records Database", layout="wide")

    # Branding banner ------------------------------------------------------
    cols = st.columns([1,3,1])
    with cols[1]:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=200)
        st.markdown("## **WRPF UK Records Database**", unsafe_allow_html=True)
        st.caption("Where Strength Meets Opportunity")

    st.caption("Use the filters on the left to browse federation records.")

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

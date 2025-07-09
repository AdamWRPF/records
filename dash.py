import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime
from PIL import UnidentifiedImageError

# ------------------------------------------------------------------
# Paths & constants
# ------------------------------------------------------------------
CSV_PATH  = Path(__file__).with_name("Records Master Sheet.csv")
LOGO_PATH = Path(__file__).with_name("wrpf_logo.png")

LIFT_MAP   = {"S": "Squat", "B": "Bench", "D": "Deadlift", "T": "Total", "Total": "Total"}
LIFT_ORDER = ["Squat", "Bench", "Deadlift", "Total"]
INVALID_WEIGHT_CLASSES = {"736", "737", "738", "739", "cell"}

DIVISION_ORDER = [
    "T14-15", "T16-17", "T18-19",
    "Junior", "Opens",
    "M40-49", "M50-59", "M60-69", "M70-79",
]

# ------------------------------------------------------------------
# Data loading & caching
# ------------------------------------------------------------------
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

    df["Lift"] = df["Lift"].replace(LIFT_MAP).fillna(df["Lift"])
    df["Date_parsed"] = pd.to_datetime(df["Date"], errors="coerce")

    for col in ["Record Type", "Lift", "Record Name"]:
        df[col] = df[col].fillna("")
    return df

# ------------------------------------------------------------------
# Sidebar filters
# ------------------------------------------------------------------
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

    # Filtering
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

# ------------------------------------------------------------------
# Best record selector
# ------------------------------------------------------------------
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

def main():
    st.set_page_config(page_title="WRPF UK Records Database", layout="centered")

    st.sidebar.markdown("""
        <style>
        section[data-testid="stSidebar"] {
            padding: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    toolbar_links = {
        "Memberships": "https://www.wrpf.uk/memberships",
        "Results":     "https://www.wrpf.uk/results",
        "Events":      "https://www.wrpf.uk/events",
        "Livestreams": "https://www.wrpf.uk/live",
    }
    cols = st.columns(len(toolbar_links))
    for col, (label, url) in zip(cols, toolbar_links.items()):
        col.markdown(f"[**{label}**]({url})", unsafe_allow_html=True)

    try:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=140)
    except UnidentifiedImageError:
        st.warning("⚠️ Logo file found but could not be opened. Please check the file format.")

    st.markdown("## **WRPF UK Records Database**")
    st.caption("Where Strength Meets Opportunity")

    st.markdown("""
        <div style='text-align:center'>
            <a href='https://www.wrpf.uk'>
                <button style='font-size:16px;padding:0.5em 1em;'>🏠 Back to WRPF.uk</button>
            </a>
        </div><br>
    """, unsafe_allow_html=True)

    df = load_data(CSV_PATH)
    filtered, sel = sidebar_filters(df)

    defaults = {k: "All" for k in ["discipline", "sex", "division", "testing_status", "equipment", "weight_class"]}
    defaults["search"] = ""
    filters_applied = any(sel[k] != defaults[k] for k in defaults)

    if filters_applied and not filtered.empty:
        st.subheader(
            f"Top Records – {sel['division'] if sel['division'] != 'All' else 'All Divisions'} – "
            f"{sel['weight_class'] if sel['weight_class'] != 'All' else 'All Weight Classes'} – "
            f"{sel['testing_status'] if sel['testing_status'] != 'All' else 'Tested & Untested'} – "
            f"{sel['equipment'] if sel['equipment'] != 'All' else 'All Equipment'}"
        )

        best = best_per_class_and_lift(filtered)
        display_df = best[[
            "Class", "Lift", "Weight", "Full Name", "Sex", "Division_base", "Equipment",
            "Testing", "Record Type", "Date", "Location"
        ]].copy()

        display_df = display_df.rename(columns={
            "Full Name":     "Name",
            "Sex":           "Gender",
            "Division_base": "Division",
            "Record Type":   "Lift Type",
            "Location":      "Event"
        })

        display_df["Lift Type"] = display_df["Lift Type"].apply(
            lambda x: "Single Lift" if str(x).lower().startswith("single") or "bench only" in str(x).lower() or "deadlift only" in str(x).lower() else "Full Power"
        )

        display_df["Weight"] = display_df["Weight"].apply(
            lambda x: int(x) if pd.notna(x) and float(x).is_integer() else x
        )

        html_table = display_df[[
            "Class", "Lift", "Weight", "Name", "Gender",
            "Division", "Equipment", "Testing",
            "Lift Type", "Date", "Event"
        ]].to_html(index=False, border=0, classes="records-table")

        st.markdown("""
            <style>
            .table-wrapper {
                overflow-x: auto;
                width: 100%;
            }
            .records-table {
                font-size: 14px;
                border-collapse: collapse;
                width: 100%;
                table-layout: auto;
            }
            @media screen and (max-width: 768px) {
                .records-table {
                    min-width: 800px;
                }
                .records-table th, .records-table td {
                    padding: 10px 6px;
                    font-size: 13px;
                }
            }
            .records-table th, .records-table td {
                border: 1px solid #ddd;
                padding: 6px;
            }
            .records-table th {
                background-color: #cf1b2b;
                color: white;
                text-align: left;
            }
            .records-table td:nth-child(4) {
                white-space: nowrap;
                max-width: 180px;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown(f'<div class="table-wrapper">{html_table}</div>', unsafe_allow_html=True)
    else:
        st.info("👈 Use the menu on the left to pick filters and see records.")

if __name__ == "__main__":
    main()

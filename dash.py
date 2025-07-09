import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime
from PIL import Image, UnidentifiedImageError

# ------------------------------------------------------------------
# Paths & constants
# ------------------------------------------------------------------
CSV_PATH = Path(__file__).with_name("Records Master Sheet.csv")
LOGO_PATH = Path(__file__).with_name("wrpf_logo.png")

LIFT_MAP = {"S": "Squat", "B": "Bench", "D": "Deadlift", "T": "Total", "Total": "Total"}
LIFT_ORDER = ["Squat", "Bench", "Deadlift", "Total"]
INVALID_WEIGHT_CLASSES = {"736", "737", "738", "739", "cell"}

DIVISION_ORDER = [
    "T14-15", "T16-17", "T18-19", "Junior", "Opens",
    "M40-49", "M50-59", "M60-69", "M70-79",
]

# ------------------------------------------------------------------
# Load Data
# ------------------------------------------------------------------
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

    params = st.query_params

    def get_param(name, fallback="All"):
        return params.get(name, fallback)

    def box(label, options, param_name):
        default = get_param(param_name)
        value = st.sidebar.selectbox(label, ["All"] + options, index=(["All"] + options).index(default) if default in options or default == "All" else 0)
        st.query_params[param_name] = value
        return value

    sel["sex"] = box("Sex", sorted(df["Sex"].dropna().unique()), "sex")

    divs = list(dict.fromkeys(df["Division_base"].unique()))
    ordered_divs = [d for d in DIVISION_ORDER if d in divs] + [d for d in divs if d not in DIVISION_ORDER]
    sel["division"] = box("Division", ordered_divs, "division")

    sel["testing_status"] = box("Testing Status", ["Tested", "Untested"], "testing")
    sel["equipment"] = box("Equipment", sorted(df["Equipment"].dropna().unique()), "equipment")

    weight_opts = sorted(df["Class"].unique(), key=lambda x: (pd.to_numeric(x, errors="coerce"), x))
    sel["weight_class"] = box("Weight Class", weight_opts, "weight")

    sel["search"] = st.sidebar.text_input("Search by name or record", value=get_param("search", ""))

    filt = df.copy()
    if sel["sex"] != "All":
        filt = filt[filt["Sex"] == sel["sex"]]
    if sel["division"] != "All":
        filt = filt[filt["Division_base"] == sel["division"]]
    if sel["testing_status"] != "All":
        filt = filt[filt["Testing"] == sel["testing_status"]]
    if sel["equipment"] != "All":
        filt = filt[filt["Equipment"] == sel["equipment"]]
    if sel["weight_class"] != "All":
        filt = filt[filt["Class"] == sel["weight_class"]]
    if sel["search"]:
        filt = filt[filt["Full Name"].str.contains(sel["search"], case=False, na=False) |
                    filt["Record Name"].str.contains(sel["search"], case=False, na=False)]

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

# ------------------------------------------------------------------
# Render table
# ------------------------------------------------------------------
def render_table(filtered, sel, key=""):
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
        "Full Name": "Name", "Sex": "Gender", "Division_base": "Division",
        "Record Type": "Lift Type", "Location": "Event"
    })

    display_df["Lift Type"] = display_df["Lift Type"].apply(
        lambda x: "Single Lift" if "single" in x.lower() or "bench only" in x.lower() or "deadlift only" in x.lower() else "Full Power"
    )
    display_df["Weight"] = display_df["Weight"].apply(
        lambda x: int(x) if pd.notna(x) and float(x).is_integer() else x
    )

    st.download_button(
        "📥 Download CSV",
        data=display_df.to_csv(index=False),
        file_name="filtered_records.csv",
        key=f"download_{key}"
    )

    html_table = display_df.to_html(index=False, border=0, classes="records-table")

    st.markdown("""
        <style>
        .records-table {
            font-size: 14px;
            border-collapse: collapse;
            width: 100%;
            table-layout: fixed;
        }
        .records-table th, .records-table td {
            border: 1px solid #ddd;
            padding: 6px;
            word-wrap: break-word;
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
        @media screen and (max-width: 768px) {
            .records-table {
                min-width: 800px;
            }
        }
        </style>
    """, unsafe_allow_html=True)
    st.markdown(f"<div>{html_table}</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    st.set_page_config("WRPF UK Records", layout="centered")

    st.markdown("""
    <div style='display: flex; gap: 1em; margin-bottom: 1em; flex-wrap: wrap'>
        <a href='https://www.wrpf.uk/memberships'><button>Memberships</button></a>
        <a href='https://www.wrpf.uk/results'><button>Results</button></a>
        <a href='https://www.wrpf.uk/events'><button>Events</button></a>
        <a href='https://www.wrpf.uk/live'><button>Livestreams</button></a>
    </div>
    """, unsafe_allow_html=True)

    try:
        if LOGO_PATH.exists():
            with Image.open(LOGO_PATH) as img:
                st.image(img, width=140)
    except (UnidentifiedImageError, OSError):
        st.warning("⚠️ Logo could not be displayed. Please check the file format.")

    st.markdown("## **WRPF UK Records Database**")
    st.caption("Where Strength Meets Opportunity")

    df = load_data(CSV_PATH)
    filtered, sel = sidebar_filters(df)

    tabs = st.tabs(["All Records", "Full Power", "Single Lifts"])

    with tabs[0]:
        render_table(filtered, sel, key="all")

    with tabs[1]:
        full_power = filtered[~filtered["Record Type"].str.contains("Single", case=False, na=False)]
        render_table(full_power, sel, key="full")

    with tabs[2]:
        mask = filtered["Record Type"].str.contains("Single|Bench Only|Deadlift Only", case=False, na=False)
        single_lifts = filtered[mask & filtered["Lift"].isin(["Bench", "Deadlift"])]
        render_table(single_lifts, sel, key="single")

if __name__ == "__main__":
    main()

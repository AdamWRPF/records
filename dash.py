import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime
from PIL import Image, UnidentifiedImageError
import streamlit.components.v1 as components

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
# Mobile detection
# ------------------------------------------------------------------
def detect_mobile():
    components.html("""
    <script>
    const isMobile = window.innerWidth < 768;
    const streamlitDoc = window.parent.document;
    streamlitDoc.dispatchEvent(new CustomEvent("streamlit:setComponentValue", {
        detail: {key: "is_mobile", value: isMobile}
    }));
    </script>
    """, height=0)

    if "is_mobile" not in st.session_state:
        st.session_state["is_mobile"] = False  # fallback default

# ------------------------------------------------------------------
# Inline filters for desktop
# ------------------------------------------------------------------
def inline_filters(df: pd.DataFrame):
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        sex = st.selectbox("Sex", ["All"] + sorted(df["Sex"].dropna().unique()))
    with col2:
        divs = list(dict.fromkeys(df["Division_base"].unique()))
        ordered_divs = [d for d in DIVISION_ORDER if d in divs] + [d for d in divs if d not in DIVISION_ORDER]
        division = st.selectbox("Division", ["All"] + ordered_divs)
    with col3:
        testing = st.selectbox("Testing", ["All", "Tested", "Untested"])
    with col4:
        equipment = st.selectbox("Equipment", ["All"] + sorted(df["Equipment"].dropna().unique()))
    with col5:
        weight_opts = sorted(df["Class"].unique(), key=lambda x: (pd.to_numeric(x, errors="coerce"), x))
        weight_class = st.selectbox("Weight", ["All"] + weight_opts)
    with col6:
        search = st.text_input("Search")

    sel = {
        "sex": sex, "division": division, "testing_status": testing,
        "equipment": equipment, "weight_class": weight_class, "search": search
    }

    return apply_filters(df, sel), sel

# ------------------------------------------------------------------
# Sidebar filters for mobile
# ------------------------------------------------------------------
def sidebar_filters(df: pd.DataFrame):
    st.sidebar.header("Filters")
    sex = st.sidebar.selectbox("Sex", ["All"] + sorted(df["Sex"].dropna().unique()))
    divs = list(dict.fromkeys(df["Division_base"].unique()))
    ordered_divs = [d for d in DIVISION_ORDER if d in divs] + [d for d in divs if d not in DIVISION_ORDER]
    division = st.sidebar.selectbox("Division", ["All"] + ordered_divs)
    testing = st.sidebar.selectbox("Testing", ["All", "Tested", "Untested"])
    equipment = st.sidebar.selectbox("Equipment", ["All"] + sorted(df["Equipment"].dropna().unique()))
    weight_opts = sorted(df["Class"].unique(), key=lambda x: (pd.to_numeric(x, errors="coerce"), x))
    weight_class = st.sidebar.selectbox("Weight", ["All"] + weight_opts)
    search = st.sidebar.text_input("Search")

    sel = {
        "sex": sex, "division": division, "testing_status": testing,
        "equipment": equipment, "weight_class": weight_class, "search": search
    }

    return apply_filters(df, sel), sel

# ------------------------------------------------------------------
# Apply filters
# ------------------------------------------------------------------
def apply_filters(df: pd.DataFrame, sel):
    filtered = df.copy()
    if sel["sex"] != "All":
        filtered = filtered[filtered["Sex"] == sel["sex"]]
    if sel["division"] != "All":
        filtered = filtered[filtered["Division_base"] == sel["division"]]
    if sel["testing_status"] != "All":
        filtered = filtered[filtered["Testing"] == sel["testing_status"]]
    if sel["equipment"] != "All":
        filtered = filtered[filtered["Equipment"] == sel["equipment"]]
    if sel["weight_class"] != "All":
        filtered = filtered[filtered["Class"] == sel["weight_class"]]
    if sel["search"]:
        filtered = filtered[
            filtered["Full Name"].str.contains(sel["search"], case=False, na=False)
            | filtered["Record Name"].str.contains(sel["search"], case=False, na=False)
        ]
    return filtered

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
            table-layout: auto;
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
            position: sticky;
            top: 0;
            z-index: 2;
        }
        .records-table td:nth-child(4) {
            white-space: normal;
            max-width: none;
            overflow: visible;
            text-overflow: unset;
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
    st.set_page_config("WRPF UK Records", layout="wide")
    detect_mobile()

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

    if st.session_state.get("is_mobile"):
        filtered, sel = sidebar_filters(df)
    else:
        filtered, sel = inline_filters(df)

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

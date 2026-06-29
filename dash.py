import pandas as pd
import streamlit as st
from pathlib import Path

MAIN_CSV_PATH = Path(__file__).with_name("Records Master Sheet.csv")
CURL_CSV_PATH = Path(__file__).with_name("curl-records.csv")
CURL_LEADERBOARD_CSV_PATH = Path(__file__).with_name("Curls.csv")
LOGO_PATH = Path(__file__).with_name("wrpf_logo.png")

LIFT_MAP = {
    "S": "Squat",
    "B": "Bench",
    "D": "Deadlift",
    "C": "Curl",
    "T": "Total",
    "Total": "Total",
}
LIFT_ORDER = ["Squat", "Bench", "Deadlift", "Curl", "Total"]
INVALID_WEIGHT_CLASSES = {"736", "737", "738", "739", "cell"}

DIVISION_ORDER = [
    "T14-15",
    "T16-17",
    "T18-19",
    "Junior",
    "Open",
    "Opens",
    "M40-49",
    "M50-59",
    "M60-69",
    "M70-79",
]

VENUE_MAP = {
    "National Championships": "United Kingdom",
    "Nottingham": "Nottingham Strong",
    "North West": "Raw Strength Gym",
    "East Coast": "Iron Warehouse Gym",
    "East Midlands": "Horncastle Powerlifting",
    "South West": "349 Barbell",
    "South Midlands": "Spartan Fitness",
    "West Midlands": "The Unit",
    "North East": "Stag Fitness Centre",
    "Welwyn Garden City": "Maverick Gym",
    "Lincoln": "Lincoln Lifting",
    "West Yorkshire": "Viking Strength Gym",
    "Peterborough": "Next Level Barbell",
    "International Event": "PHL Arena etc",
    "Specialist Event": "DOTD, Strength Wars etc",
}


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    required_columns = [
        "Full Name",
        "Weight",
        "Date",
        "Location",
        "Division",
        "Sex",
        "Class",
        "Equipment",
        "Lift",
        "Record Type",
        "Record Name",
    ]
    for column in required_columns:
        if column not in df.columns:
            df[column] = None

    df = df[df["Full Name"].notna() & df["Weight"].notna()].copy()
    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    df = df[df["Weight"].notna()].copy()

    df["Class"] = df["Class"].astype(str).str.strip()
    df = df[~df["Class"].isin(INVALID_WEIGHT_CLASSES)].copy()

    df["Division_raw"] = df["Division"].astype(str).str.strip()
    df["Division_base"] = df["Division_raw"].str.replace(r"DT$", "", regex=True)
    df["Testing"] = df["Division_raw"].str.endswith("DT").map(
        {True: "Drug Tested", False: "Untested"}
    )
    df["Lift"] = df["Lift"].replace(LIFT_MAP).fillna(df["Lift"])
    df["Date_parsed"] = pd.to_datetime(df["Date"], errors="coerce")

    df["Location"] = df["Location"].where(df["Location"].notna(), None)
    df["Location"] = df["Location"].apply(
        lambda value: value.strip() if isinstance(value, str) else value
    )

    return df


def render_filters(
    df: pd.DataFrame,
    state_key: str,
    expander_label: str = "Filters",
) -> tuple[pd.DataFrame, dict]:
    divs = list(dict.fromkeys(df["Division_base"].dropna().unique()))
    divs = [division for division in divs if "para" not in str(division).lower()]
    ordered_divs = [division for division in DIVISION_ORDER if division in divs] + [
        division for division in divs if division not in DIVISION_ORDER
    ]

    weight_opts = sorted(
        df["Class"].dropna().unique(),
        key=lambda value: (pd.to_numeric(value, errors="coerce"), value),
    )

    equipment_options = df["Equipment"].dropna().astype(str).unique()
    normalized_options = [
        "Raw" if equipment == "Bare" else equipment for equipment in equipment_options
    ]
    equipment_display = sorted(set(normalized_options))
    equipment_map = {}
    for original, display in zip(equipment_options, normalized_options):
        equipment_map.setdefault(display, set()).add(original)

    default_state = {
        "sex": "All",
        "division": "All",
        "testing_status": "All",
        "equipment": "All",
        "weight_class": "All",
        "search": "",
    }

    if state_key not in st.session_state:
        st.session_state[state_key] = default_state.copy()

    sel = st.session_state[state_key]

    with st.expander(expander_label, expanded=True):
        cols = st.columns(6)

        sex_options = ["All"] + sorted(df["Sex"].dropna().astype(str).unique())
        sel["sex"] = cols[0].selectbox(
            "Sex",
            sex_options,
            index=sex_options.index(sel["sex"]) if sel["sex"] in sex_options else 0,
            key=f"{state_key}_sex",
        )

        division_options = ["All"] + ordered_divs
        sel["division"] = cols[1].selectbox(
            "Division",
            division_options,
            index=(
                division_options.index(sel["division"])
                if sel["division"] in division_options
                else 0
            ),
            key=f"{state_key}_division",
        )

        testing_options = ["All", "Drug Tested", "Untested"]
        sel["testing_status"] = cols[2].selectbox(
            "Testing",
            testing_options,
            index=(
                testing_options.index(sel["testing_status"])
                if sel["testing_status"] in testing_options
                else 0
            ),
            key=f"{state_key}_testing",
        )

        equipment_options_display = ["All"] + equipment_display
        sel["equipment"] = cols[3].selectbox(
            "Equipment",
            equipment_options_display,
            index=(
                equipment_options_display.index(sel["equipment"])
                if sel["equipment"] in equipment_options_display
                else 0
            ),
            key=f"{state_key}_equipment",
        )

        weight_options_display = ["All"] + list(weight_opts)
        sel["weight_class"] = cols[4].selectbox(
            "Weight",
            weight_options_display,
            index=(
                weight_options_display.index(sel["weight_class"])
                if sel["weight_class"] in weight_options_display
                else 0
            ),
            key=f"{state_key}_weight",
        )

        sel["search"] = cols[5].text_input(
            "Search e.g. '110 junior'",
            value=sel["search"],
            key=f"{state_key}_search",
        )

        if st.button("Reset Filters", key=f"{state_key}_reset"):
            st.session_state[state_key] = default_state.copy()
            for suffix in [
                "sex",
                "division",
                "testing",
                "equipment",
                "weight",
                "search",
            ]:
                widget_key = f"{state_key}_{suffix}"
                if widget_key in st.session_state:
                    del st.session_state[widget_key]
            st.rerun()

    if sel["search"]:
        terms = sel["search"].lower().split()
        filtered = df.copy()
        for term in terms:
            filtered = filtered[
                filtered["Full Name"].astype(str).str.lower().str.contains(term, na=False)
                | filtered["Record Name"].astype(str).str.lower().str.contains(term, na=False)
                | filtered["Class"].astype(str).str.lower().str.contains(term, na=False)
                | filtered["Division_base"].astype(str).str.lower().str.contains(term, na=False)
                | filtered["Equipment"].astype(str).str.lower().str.contains(term, na=False)
                | filtered["Testing"].astype(str).str.lower().str.contains(term, na=False)
                | filtered["Location"].astype(str).str.lower().str.contains(term, na=False)
                | filtered["Lift"].astype(str).str.lower().str.contains(term, na=False)
            ]
        st.info("Search query detected. All filters ignored.")
        return filtered, sel

    filtered = df.copy()
    if sel["sex"] != "All":
        filtered = filtered[filtered["Sex"] == sel["sex"]]
    if sel["division"] != "All":
        filtered = filtered[filtered["Division_base"] == sel["division"]]
    if sel["testing_status"] != "All":
        filtered = filtered[filtered["Testing"] == sel["testing_status"]]
    if sel["equipment"] != "All":
        filtered = filtered[
            filtered["Equipment"].isin(sorted(equipment_map.get(sel["equipment"], [])))
        ]
    if sel["weight_class"] != "All":
        filtered = filtered[filtered["Class"] == sel["weight_class"]]

    return filtered, sel


def best_per_class_and_lift(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    return (
        df.sort_values("Weight", ascending=False)
        .drop_duplicates(subset=["Class", "Lift"])
        .assign(
            _class_num=lambda data: pd.to_numeric(data["Class"], errors="coerce"),
            _lift_order=lambda data: data["Lift"].apply(
                lambda value: LIFT_ORDER.index(value) if value in LIFT_ORDER else 99
            ),
        )
        .sort_values(["_class_num", "Class", "_lift_order"])
        .drop(columns=["_class_num", "_lift_order"])
    )


def _clean_attempt(value):
    if pd.isna(value):
        return ""

    numeric_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric_value):
        return str(value).strip()

    if float(numeric_value).is_integer():
        return str(int(numeric_value))
    return f"{numeric_value:g}"


@st.cache_data
def load_curl_leaderboard(path: Path) -> pd.DataFrame:
    """Load the strict curl results file exported in OpenPowerlifting CSV format."""
    if not path.exists():
        return pd.DataFrame()

    raw = pd.read_csv(path, header=None, dtype=str)
    header_candidates = raw.index[
        raw.apply(
            lambda row: row.astype(str).str.strip().eq("Place").any()
            and row.astype(str).str.strip().eq("Name").any(),
            axis=1,
        )
    ]

    if len(header_candidates) == 0:
        df = pd.read_csv(path, dtype=str)
    else:
        header_row = header_candidates[0]
        headers = raw.iloc[header_row].astype(str).str.strip().tolist()
        df = raw.iloc[header_row + 1 :].copy()
        df.columns = headers

    df = df.dropna(how="all").copy()
    df.columns = df.columns.astype(str).str.strip()
    df = df.loc[:, ~df.columns.str.lower().isin(["nan", "none", ""])]

    required_columns = [
        "Place",
        "Name",
        "Sex",
        "Equipment",
        "Division",
        "BodyweightKg",
        "WeightClassKg",
        "Curl1KG",
        "Curl2KG",
        "Curl3KG",
        "Best3CurlKG",
        "TotalKg",
        "Points",
    ]
    for column in required_columns:
        if column not in df.columns:
            df[column] = ""

    df = df[df["Name"].notna() & (df["Name"].astype(str).str.strip() != "")].copy()
    df["Sex"] = df["Sex"].astype(str).str.strip().str.upper()
    df = df[df["Sex"].isin(["M", "F"])].copy()

    df["Division_raw"] = df["Division"].astype(str).str.strip()
    df["Is_Drug_Tested"] = df["Division_raw"].str.contains("DT", case=False, na=False)
    df["Testing"] = df["Is_Drug_Tested"].map(
        {True: "Drug Tested", False: "Untested"}
    )
    df["Division_base"] = (
        df["Division_raw"]
        .str.replace("DT", "", case=False, regex=False)
        .str.strip()
    )

    numeric_columns = [
        "BodyweightKg",
        "Curl1KG",
        "Curl2KG",
        "Curl3KG",
        "Best3CurlKG",
        "TotalKg",
        "Points",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df[df["Best3CurlKG"].notna()].copy()
    df["WeightClassKg"] = df["WeightClassKg"].astype(str).str.strip()
    df["Equipment"] = df["Equipment"].replace({"Bare": "Raw"})
    return df


def _display_curl_leaderboard_table(df: pd.DataFrame, title: str, key: str) -> None:
    if df.empty:
        st.info(f"No {title.lower()} results found.")
        return

    sorted_df = df.sort_values(
        ["Points", "Best3CurlKG", "BodyweightKg"],
        ascending=[False, False, True],
        na_position="last",
    ).copy()
    sorted_df.insert(0, "Rank", range(1, len(sorted_df) + 1))

    display_df = sorted_df[
        [
            "Rank",
            "Name",
            "Division_base",
            "Testing",
            "Equipment",
            "BodyweightKg",
            "WeightClassKg",
            "Best3CurlKG",
            "Points",
        ]
    ].copy()

    display_df = display_df.rename(
        columns={
            "Division_base": "Division",
            "BodyweightKg": "Bodyweight",
            "WeightClassKg": "Class",
            "Best3CurlKG": "Best Weight",
        }
    )

    for column in ["Bodyweight", "Best Weight", "Points"]:
        display_df[column] = display_df[column].apply(_clean_attempt)

    display_df = display_df.fillna("")

    st.subheader(title)
    st.download_button(
        "Download CSV",
        data=display_df.to_csv(index=False),
        file_name=f"curl_leaderboard_{key}.csv",
        key=f"download_curl_leaderboard_{key}",
    )
    st.markdown(
        display_df.to_html(index=False, border=0, classes="records-table"),
        unsafe_allow_html=True,
    )


def render_curl_leaderboard(curl_leaderboard_df: pd.DataFrame) -> None:
    st.markdown("## Strict Curl Leaderboard")
    st.caption("Version: combined Men/Women leaderboard, DT and Untested shown in one Testing column.")
    st.caption(
        "Leaderboard is ranked by Points, with Best Weight used as the tie-breaker. "
        "Drug Tested and Untested athletes are shown together and identified in the Testing column."
    )

    if curl_leaderboard_df.empty:
        st.warning(
            "No curl leaderboard data found. Place the OpenPowerlifting-style results file "
            "in the same folder as this app and name it Curls.csv."
        )
        return

    st.markdown(
        """
        <style>
        .records-table {
            font-size: 14px;
            border-collapse: collapse;
            width: 100%;
            table-layout: auto;
            color: #000;
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
        .records-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .records-table tr:nth-child(odd) {
            background-color: #ffffff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    men_df = curl_leaderboard_df[curl_leaderboard_df["Sex"] == "M"].copy()
    women_df = curl_leaderboard_df[curl_leaderboard_df["Sex"] == "F"].copy()

    st.markdown("---")
    _display_curl_leaderboard_table(men_df, "Men", "men")

    st.markdown("---")
    _display_curl_leaderboard_table(women_df, "Women", "women")


def render_table(filtered: pd.DataFrame, sel: dict, key: str = "") -> None:
    show_all = bool(sel["search"])
    table_data = filtered if show_all else best_per_class_and_lift(filtered)

    st.subheader(
        f"{'All Matches' if show_all else 'Top Records'} – "
        f"{sel['division'] if sel['division'] != 'All' else 'All Divisions'} – "
        f"{sel['weight_class'] if sel['weight_class'] != 'All' else 'All Weight Classes'} – "
        f"{sel['testing_status']} – "
        f"{sel['equipment'] if sel['equipment'] != 'All' else 'All Equipment'}"
    )

    if table_data.empty:
        st.info("No records found for the selected filters.")
        return

    display_df = table_data[
        [
            "Class",
            "Lift",
            "Weight",
            "Full Name",
            "Sex",
            "Division_base",
            "Testing",
            "Equipment",
            "Record Type",
            "Date",
            "Location",
        ]
    ].copy()

    display_df = display_df.rename(
        columns={
            "Full Name": "Name",
            "Sex": "Gender",
            "Division_base": "Division",
            "Record Type": "Lift Type",
            "Location": "Event",
        }
    )

    display_df["Lift Type"] = display_df["Lift Type"].astype(str).apply(
        lambda value: (
            "Single Lift"
            if any(
                phrase in value.lower()
                for phrase in ["single", "bench only", "deadlift only", "curl only"]
            )
            else "Full Power"
        )
    )
    display_df["Weight"] = display_df["Weight"].apply(
        lambda value: int(value) if pd.notna(value) and float(value).is_integer() else value
    )
    display_df["Equipment"] = display_df["Equipment"].replace({"Bare": "Raw"})
    display_df = display_df.fillna("")

    st.download_button(
        "Download CSV",
        data=display_df.to_csv(index=False),
        file_name=f"filtered_records_{key or 'export'}.csv",
        key=f"download_{key}",
    )

    st.markdown(
        """
        <style>
        .records-table {
            font-size: 14px;
            border-collapse: collapse;
            width: 100%;
            table-layout: auto;
            color: #000;
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
        .records-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .records-table tr:nth-child(odd) {
            background-color: #ffffff;
        }
        .records-table td:nth-child(4) {
            white-space: normal;
            max-width: none;
            overflow: visible;
            text-overflow: unset;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    html_table = display_df.to_html(index=False, border=0, classes="records-table")
    st.markdown(html_table, unsafe_allow_html=True)


def main() -> None:
    st.set_page_config("WRPF UK Records", layout="wide")

    nav_cols = st.columns(4)
    nav_links = {
        "Memberships": "https://www.wrpf.uk/memberships",
        "Results": "https://www.wrpf.uk/results",
        "Events": "https://www.wrpf.uk/events",
        "Livestreams": "https://www.wrpf.uk/live",
    }
    for (label, url), col in zip(nav_links.items(), nav_cols):
        col.markdown(
            f"<a href='{url}' target='_blank'><button style='width:100%'>{label}</button></a>",
            unsafe_allow_html=True,
        )

    st.markdown("## **WRPF UK Records Database**")
    st.caption("Where Strength Meets Opportunity")

    main_df = load_data(MAIN_CSV_PATH)
    curl_df = load_data(CURL_CSV_PATH)
    curl_leaderboard_df = load_curl_leaderboard(CURL_LEADERBOARD_CSV_PATH)

    st.markdown("### Main Records Filters")
    filtered_main, main_sel = render_filters(
        main_df,
        state_key="main_records_filters",
        expander_label="Main Records Filters",
    )

    tabs = st.tabs(
        [
            "All Records",
            "Full Power",
            "Single Lifts",
            "Curls",
            "Curl Leaderboard",
            "Para",
            "Records by Region",
            "FAQ",
        ]
    )

    with tabs[0]:
        render_table(filtered_main, main_sel, key="all")

    with tabs[1]:
        full_power = filtered_main[
            ~filtered_main["Record Type"].astype(str).str.contains("Single", case=False, na=False)
        ]
        render_table(full_power, main_sel, key="full")

    with tabs[2]:
        mask = filtered_main["Record Type"].astype(str).str.contains(
            "Single|Bench Only|Deadlift Only",
            case=False,
            na=False,
        )
        single_lifts = filtered_main[
            mask & filtered_main["Lift"].isin(["Bench", "Deadlift"])
        ]
        render_table(single_lifts, main_sel, key="single")

    with tabs[3]:
        st.markdown("### Curl Records Filters")
        filtered_curls, curl_sel = render_filters(
            curl_df,
            state_key="curl_records_filters",
            expander_label="Curl Records Filters",
        )
        curls_only = filtered_curls[filtered_curls["Lift"] == "Curl"]
        render_table(curls_only, curl_sel, key="curls")

    with tabs[4]:
        render_curl_leaderboard(curl_leaderboard_df)

    with tabs[5]:
        st.markdown("## ♿ Para Bench Press Records")
        st.markdown(
            """
            <div style="
                border-left: 5px solid #cf1b2b;
                background-color: rgba(255,255,255,0.05);
                padding: 1rem;
                margin-bottom: 1.5rem;
                font-size: 16px;
                border-radius: 6px;
                color: #fff;">
                <strong>Note:</strong> If there is no record for your division as a Para athlete, the weight you lift will become the new record.
            </div>
            """,
            unsafe_allow_html=True,
        )

        para_bench = filtered_main[
            (filtered_main["Lift"] == "Bench")
            & (filtered_main["Division_raw"].str.contains("para", case=False, na=False))
        ]
        if not para_bench.empty:
            render_table(para_bench, main_sel, key="para")
        else:
            st.info("No Para Bench Press records found.")

    with tabs[6]:
        st.markdown("## 📍 Records by Region")
        region_df = (
            main_df[main_df["Location"].notna() & (main_df["Location"].str.strip() != "")]
            .groupby("Location")
            .size()
            .reset_index(name="Records")
        )
        region_df["Venue"] = region_df["Location"].map(VENUE_MAP)
        region_df = region_df[region_df["Venue"].notna()]
        region_df = region_df.rename(columns={"Location": "Region"})
        specialist_events = region_df[region_df["Region"] == "Specialist Event"]
        region_df = region_df[region_df["Region"] != "Specialist Event"]
        region_df = pd.concat(
            [region_df.sort_values("Records", ascending=False), specialist_events],
            ignore_index=True,
        )
        st.markdown(
            region_df[["Region", "Venue", "Records"]].to_html(
                index=False,
                border=0,
                classes="records-table",
            ),
            unsafe_allow_html=True,
        )

    with tabs[7]:
        st.markdown("## ❓ Frequently Asked Questions")
        st.markdown(
            """
**Q: How often is this database updated?**  
A: We update the records shortly after each WRPF UK sanctioned event.

**Q: What does 'Drug Tested' mean?**  
A: It refers to divisions where athletes are subject to in-competition testing.

**Q: What is the difference between Raw, Sleeves, Wraps, Single-ply and Multi-ply?**  
A: Raw means no supportive equipment beyond belt and wrist wraps.  
Sleeves = knee sleeves; Wraps = knee wraps.  
Single-ply and Multi-ply refer to supportive suits made with one or multiple layers of material.

**Q: How can I get a record updated or corrected?**  
A: Please contact [events@wrpf.uk](mailto:events@wrpf.uk) with evidence or questions.

**Q: What does Standard mean?**  
A: This is just a record standard selected from OpenPowerlifting data.  
To claim this record, you must break it by 0.5kg at any WRPF UK event.
            """
        )


if __name__ == "__main__":
    main()

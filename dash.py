[previous unchanged code above remains here]

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
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

        st.download_button(
            label="Download filtered records as CSV",
            data=display_df.to_csv(index=False),
            file_name="filtered_wrpf_records.csv",
            mime="text/csv"
        )

        html_table = display_df[[
            "Class", "Lift", "Weight", "Name", "Gender",
            "Division", "Equipment", "Testing",
            "Lift Type", "Date", "Event"
        ]].to_html(index=False, border=0, classes="records-table")

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
    else:
        st.info("👈 Use the menu on the left to pick filters and see records.")

if __name__ == "__main__":
    main()

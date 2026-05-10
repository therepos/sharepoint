"""Family page — ISD CAT2 screening data."""
import streamlit as st

from app import db


def render():
    st.title("Family")
    st.warning("⚠️ Highly sensitive — used only for ISD CAT2 screening forms.")

    # Filter by personnel
    staff_options = db.fetch_all(
        "SELECT personnel_id, full_name FROM personnel ORDER BY full_name"
    )
    staff_filter = st.selectbox(
        "Show family members for",
        ["(all)"] + [f"{s['full_name']} ({s['personnel_id']})" for s in staff_options],
    )

    query = """
        SELECT f.*, p.full_name AS staff_name
        FROM family f LEFT JOIN personnel p ON f.personnel_id = p.personnel_id
    """
    params: tuple = ()
    if staff_filter != "(all)":
        pid = staff_filter.split("(")[-1].rstrip(")")
        query += " WHERE f.personnel_id = ?"
        params = (pid,)
    query += " ORDER BY f.personnel_id, f.relationship"

    df = db.fetch_df(query, params)
    st.caption(f"{len(df)} records")

    if df.empty:
        st.info("No family records.")
    else:
        st.dataframe(
            df[["personnel_id", "staff_name", "family_member_name", "relationship",
                "id_number", "citizenship", "dob"]],
            use_container_width=True,
        )

    st.divider()
    st.caption("To add or edit family records, use the Bulk Import page.")

"""PII page — separate from main staff page due to sensitivity."""
import streamlit as st

from app import db


def render():
    st.title("PII")
    st.warning("⚠️ Sensitive personal data (NRIC, DOB, citizenship). Handle with care.")

    # List
    df = db.fetch_df(
        """
        SELECT pi.personnel_id, p.full_name, pi.nric_passport, pi.citizenship,
               pi.pr_status, pi.fin_holder, pi.dob
        FROM pii pi
        LEFT JOIN personnel p ON pi.personnel_id = p.personnel_id
        ORDER BY pi.personnel_id
        """
    )

    c1, c2 = st.columns([4, 1])
    with c1:
        st.caption(f"{len(df)} PII records")
    with c2:
        if st.button("➕ Add / Edit PII", type="primary", use_container_width=True):
            st.session_state["edit_pii_id"] = "__new__"
            st.rerun()

    if "edit_pii_id" in st.session_state:
        _render_edit_form(st.session_state["edit_pii_id"])
        return

    if df.empty:
        st.info("No PII records yet.")
        return

    for _, row in df.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1, 3, 2, 2, 2, 1])
        with c1:
            st.text(row["personnel_id"])
        with c2:
            st.text(row["full_name"] or "(no staff record)")
        with c3:
            st.text(row["nric_passport"])
        with c4:
            st.text(row["citizenship"])
        with c5:
            st.text(f"PR:{row['pr_status']} FIN:{row['fin_holder']}")
        with c6:
            if st.button("Edit", key=f"editpii_{row['personnel_id']}"):
                st.session_state["edit_pii_id"] = row["personnel_id"]
                st.rerun()


def _render_edit_form(personnel_id: str):
    is_new = personnel_id == "__new__"

    if is_new:
        st.subheader("Add PII record")
        # Pick personnel from dropdown
        staff = db.fetch_all(
            """
            SELECT p.personnel_id, p.full_name, p.alias_name
            FROM personnel p
            LEFT JOIN pii pi ON p.personnel_id = pi.personnel_id
            WHERE pi.personnel_id IS NULL
            ORDER BY p.full_name
            """
        )
        if not staff:
            st.info("All staff already have PII records. Pick from list to edit.")
            if st.button("Cancel"):
                del st.session_state["edit_pii_id"]
                st.rerun()
            return
        choice = st.selectbox(
            "Staff",
            [f"{s['full_name']} ({s['personnel_id']})" for s in staff],
        )
        chosen_pid = choice.split("(")[-1].rstrip(")") if choice else None
        record = {
            "personnel_id": chosen_pid or "",
            "nric_passport": "", "other_id": "", "pr_status": "N", "fin_holder": "N",
            "citizenship": "", "place_of_birth": "", "dob": "",
            "designation": "", "company": "Ernst & Young Advisory Pte Ltd",
        }
    else:
        record = db.fetch_one("SELECT * FROM pii WHERE personnel_id = ?", (personnel_id,))
        if not record:
            st.error("Not found")
            del st.session_state["edit_pii_id"]
            return
        st.subheader(f"Edit PII for {personnel_id}")

    with st.form("pii_form"):
        c1, c2 = st.columns(2)
        with c1:
            nric = st.text_input("NRIC / Passport", value=record["nric_passport"])
            other_id = st.text_input("Other ID", value=record["other_id"])
            pr = st.selectbox("PR status", ["", "Y", "N"],
                              index=["", "Y", "N"].index(record.get("pr_status", "")))
            fin = st.selectbox("FIN holder", ["", "Y", "N"],
                               index=["", "Y", "N"].index(record.get("fin_holder", "")))
            citizenship = st.text_input("Citizenship", value=record["citizenship"])
        with c2:
            pob = st.text_input("Place of birth", value=record["place_of_birth"])
            dob = st.text_input("DOB (YYYYMMDD)", value=record["dob"])
            designation = st.text_input("Designation", value=record["designation"])
            company = st.text_input("Company", value=record["company"])

        c1, c2, c3 = st.columns([1, 1, 3])
        with c1:
            save = st.form_submit_button("Save", type="primary")
        with c2:
            cancel = st.form_submit_button("Cancel")
        with c3:
            if not is_new:
                delete_btn = st.form_submit_button("🗑️ Delete", type="secondary")
            else:
                delete_btn = False

    if save:
        data = {
            "nric_passport": nric, "other_id": other_id, "pr_status": pr, "fin_holder": fin,
            "citizenship": citizenship, "place_of_birth": pob, "dob": dob,
            "designation": designation, "company": company,
        }
        if is_new:
            data["personnel_id"] = record["personnel_id"]
            db.insert("pii", data)
        else:
            db.update("pii", "personnel_id", personnel_id, data)
        st.success("Saved")
        del st.session_state["edit_pii_id"]
        st.rerun()

    if cancel:
        del st.session_state["edit_pii_id"]
        st.rerun()

    if delete_btn:
        db.delete("pii", "personnel_id", personnel_id)
        st.success("Deleted")
        del st.session_state["edit_pii_id"]
        st.rerun()

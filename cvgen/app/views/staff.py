"""Staff CRUD page."""
import streamlit as st

from app import db


def render():
    st.title("Staff")

    # Search bar + Add button
    c1, c2 = st.columns([4, 1])
    with c1:
        search = st.text_input("Search by name or ID", placeholder="e.g. Ann Sheng or P001",
                               label_visibility="collapsed")
    with c2:
        if st.button("➕ Add staff", type="primary", use_container_width=True):
            st.session_state["edit_staff_id"] = "__new__"
            st.rerun()

    # Edit form (when a row is selected)
    if "edit_staff_id" in st.session_state:
        _render_edit_form(st.session_state["edit_staff_id"])
        return

    # Listing
    query = "SELECT * FROM personnel"
    params: tuple = ()
    if search:
        query += " WHERE full_name LIKE ? OR alias_name LIKE ? OR personnel_id LIKE ?"
        like = f"%{search}%"
        params = (like, like, like)
    query += " ORDER BY personnel_id"

    df = db.fetch_df(query, params)
    if df.empty:
        st.info("No staff found.")
        return

    st.caption(f"{len(df)} staff — tick rows to select, then Edit / Delete")

    display_df = df[["personnel_id", "full_name", "alias_name", "position", "department"]].copy()
    display_df = display_df.rename(columns={
        "personnel_id": "ID",
        "full_name": "Name",
        "alias_name": "Alias",
        "position": "Position",
        "department": "Department",
    })

    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="staff_table",
    )

    selected_rows = list(event.selection.rows) if event and event.selection else []
    selected_ids = [df.iloc[i]["personnel_id"] for i in selected_rows]

    c1, c2, c3, _ = st.columns([1, 1.4, 1.4, 4])
    with c1:
        if st.button("Edit", disabled=len(selected_ids) != 1, use_container_width=True):
            st.session_state["edit_staff_id"] = selected_ids[0]
            st.rerun()
    with c2:
        if st.button(f"🗑️ Delete selected ({len(selected_ids)})",
                     disabled=not selected_ids, use_container_width=True):
            st.session_state["confirm_delete_ids"] = selected_ids
            st.rerun()
    with c3:
        if st.button("🗑️ Delete ALL staff", type="secondary", use_container_width=True):
            st.session_state["confirm_delete_all"] = True
            st.rerun()

    _render_delete_confirmations()


def _render_delete_confirmations():
    if st.session_state.get("confirm_delete_ids"):
        ids = st.session_state["confirm_delete_ids"]
        st.warning(
            f"Delete {len(ids)} staff record(s)? This also removes their education, "
            f"certifications, employment, assignments, PII, and family rows (cascade)."
        )
        c1, c2, _ = st.columns([1, 1, 5])
        with c1:
            if st.button("Confirm delete", type="primary"):
                for pid in ids:
                    db.delete("personnel", "personnel_id", pid)
                del st.session_state["confirm_delete_ids"]
                st.success(f"Deleted {len(ids)} staff")
                st.rerun()
        with c2:
            if st.button("Cancel"):
                del st.session_state["confirm_delete_ids"]
                st.rerun()

    if st.session_state.get("confirm_delete_all"):
        st.error(
            "Delete **ALL** staff records? This wipes personnel and cascades to "
            "education, certifications, employment, assignments, PII, and family. "
            "This cannot be undone."
        )
        confirm_text = st.text_input(
            "Type DELETE ALL to confirm", key="confirm_delete_all_text"
        )
        c1, c2, _ = st.columns([1, 1, 5])
        with c1:
            if st.button("Confirm wipe", type="primary",
                         disabled=confirm_text != "DELETE ALL"):
                db.execute("DELETE FROM personnel")
                del st.session_state["confirm_delete_all"]
                st.session_state.pop("confirm_delete_all_text", None)
                st.success("All staff deleted")
                st.rerun()
        with c2:
            if st.button("Cancel", key="cancel_delete_all"):
                del st.session_state["confirm_delete_all"]
                st.session_state.pop("confirm_delete_all_text", None)
                st.rerun()


def _render_edit_form(personnel_id: str):
    is_new = personnel_id == "__new__"
    if is_new:
        st.subheader("Add new staff")
        record = {
            "personnel_id": db.next_id("personnel", "P", "personnel_id"),
            "full_name": "", "alias_name": "", "nationality": "",
            "position": "Senior Consultant", "department": "Risk Consulting",
            "role": "Team member", "start_year": 2025,
            "active": "Yes", "generate": "No", "notes": "",
        }
    else:
        record = db.fetch_one("SELECT * FROM personnel WHERE personnel_id = ?", (personnel_id,))
        if not record:
            st.error("Not found")
            del st.session_state["edit_staff_id"]
            return
        st.subheader(f"Edit {record['full_name']} ({record['personnel_id']})")

    with st.form("staff_form"):
        c1, c2 = st.columns(2)
        with c1:
            personnel_id_val = st.text_input("Personnel ID", value=record["personnel_id"], disabled=not is_new)
            full_name = st.text_input("Full name (legal)", value=record["full_name"])
            alias_name = st.text_input("Alias name", value=record.get("alias_name", ""))
            nationality = st.text_input("Nationality", value=record.get("nationality", ""))
            position = st.selectbox(
                "Position",
                ["Consultant", "Senior Consultant", "Manager", "Senior Manager", "Director", "Partner"],
                index=["Consultant", "Senior Consultant", "Manager", "Senior Manager", "Director", "Partner"].index(
                    record.get("position", "Senior Consultant")
                ) if record.get("position") in ["Consultant", "Senior Consultant", "Manager", "Senior Manager", "Director", "Partner"] else 1,
            )
        with c2:
            department = st.text_input("Department", value=record.get("department", "Risk Consulting"))
            role = st.text_input("Default role", value=record.get("role", ""))
            start_year = st.number_input("Start year", min_value=1990, max_value=2100,
                                          value=int(record.get("start_year") or 2025))
            active = st.selectbox("Active", ["Yes", "No"],
                                  index=0 if record.get("active") == "Yes" else 1)
            generate = st.selectbox("Generate Annex E", ["Yes", "No"],
                                     index=0 if record.get("generate") == "Yes" else 1)
        notes = st.text_area("Notes", value=record.get("notes", ""))

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
            "full_name": full_name, "alias_name": alias_name, "nationality": nationality,
            "position": position, "department": department, "role": role,
            "start_year": start_year, "active": active, "generate": generate, "notes": notes,
        }
        if is_new:
            data["personnel_id"] = personnel_id_val
            db.insert("personnel", data)
            st.success(f"Created {personnel_id_val}")
        else:
            db.update("personnel", "personnel_id", personnel_id, data)
            st.success("Saved")
        del st.session_state["edit_staff_id"]
        st.rerun()

    if cancel:
        del st.session_state["edit_staff_id"]
        st.rerun()

    if delete_btn:
        db.delete("personnel", "personnel_id", personnel_id)
        st.success("Deleted")
        del st.session_state["edit_staff_id"]
        st.rerun()

    # Show related data (read-only summaries)
    if not is_new:
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Education**")
            edu = db.fetch_df("SELECT * FROM education WHERE personnel_id = ?", (personnel_id,))
            if not edu.empty:
                for _, e in edu.iterrows():
                    st.markdown(f"- {e['course_name']}, {e['institution']} ({e['year_attained']})")
            else:
                st.caption("None")

            st.markdown("**Certifications**")
            cert = db.fetch_df("SELECT * FROM certifications WHERE personnel_id = ?", (personnel_id,))
            if not cert.empty:
                for _, c in cert.iterrows():
                    st.markdown(f"- {c['name']} ({c['year_attained']})")
            else:
                st.caption("None")
        with c2:
            st.markdown("**Projects assigned**")
            asg = db.fetch_df(
                """
                SELECT a.role_on_project, p.project_id, p.client_name, p.project_name
                FROM assignments a JOIN projects p ON a.project_id = p.project_id
                WHERE a.personnel_id = ?
                ORDER BY p.start_period DESC
                """,
                (personnel_id,),
            )
            if not asg.empty:
                for _, a in asg.iterrows():
                    st.markdown(f"- **{a['client_name']}** — {a['project_name']} ({a['role_on_project']})")
            else:
                st.caption("None")
        st.caption("To edit education, certifications, employment, or assignments, use the Assignments page or run bulk import.")

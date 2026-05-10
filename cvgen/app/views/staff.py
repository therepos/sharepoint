"""Staff CRUD page — also handles PII and Family records inline."""
from __future__ import annotations

from datetime import date

import streamlit as st

from app import db


POSITIONS = ["Consultant", "Senior Consultant", "Manager", "Senior Manager", "Director", "Partner"]


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

    if "edit_staff_id" in st.session_state:
        _render_edit_form(st.session_state["edit_staff_id"])
        return

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


# ---------------------------------------------------------------------------
# Staff edit form
# ---------------------------------------------------------------------------
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

    if is_new:
        _render_profile_form(record, is_new=True)
        return

    # Existing record: tabbed view (Profile / PII / Family / Projects)
    profile_tab, pii_tab, family_tab, projects_tab = st.tabs(
        ["Profile", "PII", "Family", "Projects assigned"]
    )
    with profile_tab:
        _render_profile_form(record, is_new=False)
    with pii_tab:
        _render_pii_section(personnel_id)
    with family_tab:
        _render_family_section(personnel_id)
    with projects_tab:
        _render_projects_assigned(personnel_id)


def _render_profile_form(record: dict, is_new: bool):
    personnel_id = record["personnel_id"]
    with st.form("staff_form"):
        c1, c2 = st.columns(2)
        with c1:
            personnel_id_val = st.text_input("Personnel ID", value=record["personnel_id"], disabled=not is_new)
            full_name = st.text_input("Full name (legal)", value=record["full_name"])
            alias_name = st.text_input("Alias name", value=record.get("alias_name", ""))
            nationality = st.text_input("Nationality", value=record.get("nationality", ""))
            position_value = record.get("position") or "Senior Consultant"
            position = st.selectbox(
                "Position", POSITIONS,
                index=POSITIONS.index(position_value) if position_value in POSITIONS else 1,
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
            st.session_state["edit_staff_id"] = personnel_id_val
        else:
            db.update("personnel", "personnel_id", personnel_id, data)
            st.success("Saved")
        st.rerun()

    if cancel:
        del st.session_state["edit_staff_id"]
        st.rerun()

    if delete_btn:
        db.delete("personnel", "personnel_id", personnel_id)
        st.success("Deleted")
        del st.session_state["edit_staff_id"]
        st.rerun()


# ---------------------------------------------------------------------------
# PII section (formerly its own page)
# ---------------------------------------------------------------------------
def _render_pii_section(personnel_id: str):
    st.warning("⚠️ Sensitive personal data (NRIC, DOB, citizenship). Handle with care.")

    record = db.fetch_one("SELECT * FROM pii WHERE personnel_id = ?", (personnel_id,))
    is_new_pii = record is None
    if record is None:
        record = {
            "personnel_id": personnel_id,
            "nric_passport": "", "other_id": "", "pr_status": "N", "fin_holder": "N",
            "citizenship": "", "place_of_birth": "", "dob": "",
            "designation": "", "company": "Ernst & Young Advisory Pte Ltd",
        }

    with st.form(f"pii_form_{personnel_id}"):
        c1, c2 = st.columns(2)
        with c1:
            nric = st.text_input("NRIC / Passport", value=record["nric_passport"])
            other_id = st.text_input("Other ID", value=record["other_id"])
            pr = st.selectbox("PR status", ["", "Y", "N"],
                              index=["", "Y", "N"].index(record.get("pr_status") or ""))
            fin = st.selectbox("FIN holder", ["", "Y", "N"],
                               index=["", "Y", "N"].index(record.get("fin_holder") or ""))
            citizenship = _dropdown_with_add(
                "Citizenship", record["citizenship"],
                _distinct_pii_values("citizenship"),
                key_prefix=f"pii_cit_{personnel_id}",
            )
        with c2:
            pob = _dropdown_with_add(
                "Place of birth", record["place_of_birth"],
                _distinct_pii_values("place_of_birth"),
                key_prefix=f"pii_pob_{personnel_id}",
            )
            dob_default = _parse_yyyymmdd(record.get("dob"))
            dob_picked = st.date_input(
                "Date of birth",
                value=dob_default,
                min_value=date(1900, 1, 1),
                max_value=date.today(),
                format="YYYY-MM-DD",
            )
            designation = _dropdown_with_add(
                "Designation", record["designation"],
                _distinct_pii_values("designation"),
                key_prefix=f"pii_desig_{personnel_id}",
            )
            company = _dropdown_with_add(
                "Company", record["company"],
                _distinct_pii_values("company"),
                key_prefix=f"pii_co_{personnel_id}",
            )

        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            save = st.form_submit_button("Save PII", type="primary")
        with c2:
            delete_btn = st.form_submit_button(
                "🗑️ Delete PII", type="secondary", disabled=is_new_pii
            )

    if save:
        data = {
            "nric_passport": nric, "other_id": other_id, "pr_status": pr, "fin_holder": fin,
            "citizenship": citizenship, "place_of_birth": pob,
            "dob": _format_yyyymmdd(dob_picked),
            "designation": designation, "company": company,
        }
        if is_new_pii:
            data["personnel_id"] = personnel_id
            db.insert("pii", data)
        else:
            db.update("pii", "personnel_id", personnel_id, data)
        st.success("Saved")
        st.rerun()

    if delete_btn and not is_new_pii:
        db.delete("pii", "personnel_id", personnel_id)
        st.success("PII deleted")
        st.rerun()


# ---------------------------------------------------------------------------
# Family section (formerly its own page)
# ---------------------------------------------------------------------------
def _render_family_section(personnel_id: str):
    st.warning("⚠️ Highly sensitive — used only for ISD CAT2 screening forms.")

    df = db.fetch_df(
        "SELECT * FROM family WHERE personnel_id = ? ORDER BY relationship, family_member_name",
        (personnel_id,),
    )

    if df.empty:
        st.caption("No family members on file.")
    else:
        for _, row in df.iterrows():
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
            with c1:
                st.text(row["family_member_name"])
            with c2:
                st.text(row["relationship"] or "—")
            with c3:
                st.text(row["citizenship"] or "—")
            with c4:
                st.text(row["dob"] or "—")
            with c5:
                if st.button("Remove", key=f"rm_fam_{row['family_id']}"):
                    db.delete("family", "family_id", row["family_id"])
                    st.rerun()

    st.markdown("**Add family member**")
    with st.form(f"add_family_{personnel_id}", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full name")
            relationship = st.selectbox(
                "Relationship",
                ["", "Spouse", "Father", "Mother", "Son", "Daughter",
                 "Brother", "Sister", "Other"],
            )
            id_type = st.selectbox(
                "ID type",
                ["", "NRIC", "FIN", "Passport", "Birth Cert", "Other"],
            )
            id_number = st.text_input("ID number")
            citizenship = st.text_input("Citizenship")
        with c2:
            pr_status = st.selectbox("PR status", ["", "Y", "N"])
            workpass_holder = st.selectbox("Work-pass holder", ["", "Y", "N"])
            gender = st.selectbox("Gender", ["", "M", "F"])
            dob = st.date_input(
                "Date of birth",
                value=None,
                min_value=date(1900, 1, 1),
                max_value=date.today(),
                format="YYYY-MM-DD",
            )
            country_of_birth = st.text_input("Country of birth")
        submitted = st.form_submit_button("Add family member", type="primary")

    if submitted:
        if not name.strip():
            st.error("Family member name is required.")
            return
        try:
            db.insert("family", {
                "family_id": db.next_id("family", "F", "family_id"),
                "personnel_id": personnel_id,
                "family_member_name": name.strip(),
                "relationship": relationship,
                "id_type": id_type,
                "id_number": id_number,
                "citizenship": citizenship,
                "pr_status": pr_status,
                "workpass_holder": workpass_holder,
                "gender": gender,
                "dob": _format_yyyymmdd(dob),
                "country_of_birth": country_of_birth,
            })
            st.success("Family member added")
            st.rerun()
        except Exception as e:
            st.error(f"Failed: {e}")


# ---------------------------------------------------------------------------
# Projects-assigned read-only summary
# ---------------------------------------------------------------------------
def _render_projects_assigned(personnel_id: str):
    edu = db.fetch_df("SELECT * FROM education WHERE personnel_id = ?", (personnel_id,))
    cert = db.fetch_df("SELECT * FROM certifications WHERE personnel_id = ?", (personnel_id,))
    asg = db.fetch_df(
        """
        SELECT a.role_on_project, p.project_id, p.client_name, p.project_name
        FROM assignments a JOIN projects p ON a.project_id = p.project_id
        WHERE a.personnel_id = ?
        ORDER BY p.start_period DESC
        """,
        (personnel_id,),
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Education**")
        if not edu.empty:
            for _, e in edu.iterrows():
                st.markdown(f"- {e['course_name']}, {e['institution']} ({e['year_attained']})")
        else:
            st.caption("None")

        st.markdown("**Certifications**")
        if not cert.empty:
            for _, c in cert.iterrows():
                st.markdown(f"- {c['name']} ({c['year_attained']})")
        else:
            st.caption("None")
    with c2:
        st.markdown("**Projects assigned**")
        if not asg.empty:
            for _, a in asg.iterrows():
                st.markdown(f"- **{a['client_name']}** — {a['project_name']} ({a['role_on_project']})")
        else:
            st.caption("None")
    st.caption(
        "To edit education, certifications, or employment, use Bulk Import. "
        "To assign this person to a project, edit the project."
    )


# ---------------------------------------------------------------------------
# Date helpers (DOB stored as YYYYMMDD text)
# ---------------------------------------------------------------------------
def _parse_yyyymmdd(val: str | None) -> date | None:
    if not val:
        return None
    s = val.strip().replace("-", "")
    if len(s) != 8 or not s.isdigit():
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except ValueError:
        return None


def _format_yyyymmdd(d: date | None) -> str:
    if not d:
        return ""
    return f"{d.year:04d}{d.month:02d}{d.day:02d}"


# ---------------------------------------------------------------------------
# Dropdown-with-add helpers (for free-form fields with reusable values)
# ---------------------------------------------------------------------------
def _distinct_pii_values(column: str) -> list[str]:
    rows = db.fetch_all(
        f"SELECT DISTINCT {column} AS v FROM pii "
        f"WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}"
    )
    return [r["v"] for r in rows]


def _dropdown_with_add(label: str, current: str, options: list[str], key_prefix: str) -> str:
    """Selectbox of existing values + always-visible 'add new' text input.

    Form-safe: works inside st.form (no rerun-on-change required).
    The new-value box wins if the user typed anything in it.
    """
    current = (current or "").strip()
    merged: list[str] = []
    for v in options:
        if v and v not in merged:
            merged.append(v)
    if current and current not in merged:
        merged.insert(0, current)
    if not merged:
        merged = [""]
    default_idx = merged.index(current) if current in merged else 0

    selected = st.selectbox(label, merged, index=default_idx, key=f"{key_prefix}_select")
    new_val = st.text_input(
        f"➕ Add new {label.lower()}", value="", key=f"{key_prefix}_new",
        placeholder="Type here to override the dropdown",
    )
    return new_val.strip() if new_val.strip() else selected

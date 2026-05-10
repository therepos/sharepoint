"""Projects CRUD page."""
import streamlit as st

from app import db


PROJECT_TYPES = ["internal_audit", "iso", "ssae3402", "other"]


def render():
    st.title("Projects")

    c1, c2 = st.columns([4, 1])
    with c1:
        search = st.text_input("Search by client or project name",
                               placeholder="e.g. MOE or PRJ003",
                               label_visibility="collapsed")
    with c2:
        if st.button("➕ Add project", type="primary", use_container_width=True):
            st.session_state["edit_project_id"] = "__new__"
            st.rerun()

    if "edit_project_id" in st.session_state:
        _render_edit_form(st.session_state["edit_project_id"])
        return

    query = "SELECT * FROM projects"
    params: tuple = ()
    if search:
        query += " WHERE client_name LIKE ? OR project_name LIKE ? OR project_id LIKE ?"
        like = f"%{search}%"
        params = (like, like, like)
    query += " ORDER BY project_id"

    df = db.fetch_df(query, params)
    if df.empty:
        st.info("No projects.")
        return

    st.caption(f"{len(df)} projects")
    for _, row in df.iterrows():
        c1, c2, c3, c4 = st.columns([1, 3, 4, 1])
        with c1:
            st.text(row["project_id"])
        with c2:
            st.text(row["client_name"])
        with c3:
            st.text(row["project_name"])
        with c4:
            if st.button("Edit", key=f"editproj_{row['project_id']}"):
                st.session_state["edit_project_id"] = row["project_id"]
                st.rerun()


def _render_edit_form(project_id: str):
    is_new = project_id == "__new__"
    if is_new:
        st.subheader("Add new project")
        record = {
            "project_id": db.next_id("projects", "PRJ", "project_id"),
            "client_name": "", "project_name": "", "description": "",
            "start_period": "", "end_period": "present",
            "project_type": "internal_audit", "sector_tags": "", "scope_areas": "",
        }
    else:
        record = db.fetch_one("SELECT * FROM projects WHERE project_id = ?", (project_id,))
        if not record:
            st.error("Not found")
            del st.session_state["edit_project_id"]
            return
        st.subheader(f"Edit {record['client_name']} ({project_id})")

    with st.form("project_form"):
        c1, c2 = st.columns(2)
        with c1:
            project_id_val = st.text_input("Project ID", value=record["project_id"], disabled=not is_new)
            client_name = st.text_input("Client name", value=record["client_name"])
            project_name = st.text_input("Project name", value=record["project_name"])
            project_type = st.selectbox("Type", PROJECT_TYPES,
                                         index=PROJECT_TYPES.index(record.get("project_type", "internal_audit")))
        with c2:
            start_period = st.text_input("Start period (YYYY-MM)", value=record.get("start_period", ""))
            end_period = st.text_input("End period (YYYY-MM or 'present')", value=record.get("end_period", ""))
            sector_tags = st.text_input("Sector tags (comma-sep)", value=record.get("sector_tags", ""),
                                         help="e.g. government,charity")
            scope_areas = st.text_input("Scope areas (comma-sep)", value=record.get("scope_areas", ""),
                                         help="e.g. procurement,grants,governance")
        description = st.text_area("Description", value=record.get("description", ""), height=120,
                                    help="Leave blank, generate via LLM externally, paste back.")

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
            "client_name": client_name, "project_name": project_name,
            "description": description, "start_period": start_period, "end_period": end_period,
            "project_type": project_type, "sector_tags": sector_tags, "scope_areas": scope_areas,
        }
        if is_new:
            data["project_id"] = project_id_val
            db.insert("projects", data)
            st.success(f"Created {project_id_val}")
        else:
            db.update("projects", "project_id", project_id, data)
            st.success("Saved")
        del st.session_state["edit_project_id"]
        st.rerun()

    if cancel:
        del st.session_state["edit_project_id"]
        st.rerun()

    if delete_btn:
        db.delete("projects", "project_id", project_id)
        st.success("Deleted")
        del st.session_state["edit_project_id"]
        st.rerun()

    # Team summary
    if not is_new:
        st.divider()
        st.markdown("**Team assigned**")
        team = db.fetch_df(
            """
            SELECT p.personnel_id, p.full_name, p.alias_name, a.role_on_project
            FROM assignments a JOIN personnel p ON a.personnel_id = p.personnel_id
            WHERE a.project_id = ?
            ORDER BY p.full_name
            """,
            (project_id,),
        )
        if not team.empty:
            for _, t in team.iterrows():
                display = t["full_name"]
                if t.get("alias_name"):
                    display += f" ({t['alias_name']})"
                st.markdown(f"- {display} — _{t['role_on_project']}_")
        else:
            st.caption("No team assigned. Use Assignments page to add.")

"""Assignments page — link staff to projects via a friendly form."""
import streamlit as st

from app import db


def render():
    st.title("Assignments")
    st.caption("Link staff to projects with their role.")

    # Quick-add form at top
    with st.expander("➕ Add new assignment", expanded=False):
        _render_add_form()

    # List + filters
    c1, c2 = st.columns(2)
    with c1:
        staff_options = db.fetch_all(
            "SELECT personnel_id, full_name, alias_name FROM personnel ORDER BY full_name"
        )
        staff_filter = st.selectbox(
            "Filter by staff",
            ["(all)"] + [_label(s) for s in staff_options],
        )
    with c2:
        project_options = db.fetch_all(
            "SELECT project_id, client_name, project_name FROM projects ORDER BY client_name"
        )
        project_filter = st.selectbox(
            "Filter by project",
            ["(all)"] + [f"{p['client_name']} — {p['project_name']} ({p['project_id']})"
                        for p in project_options],
        )

    query = """
        SELECT a.personnel_id, p.full_name, p.alias_name,
               a.project_id, pr.client_name, pr.project_name,
               a.role_on_project, a.contribution_notes
        FROM assignments a
        JOIN personnel p ON a.personnel_id = p.personnel_id
        JOIN projects pr ON a.project_id = pr.project_id
    """
    where = []
    params: list = []
    if staff_filter != "(all)":
        pid = staff_filter.split("(")[-1].rstrip(")")
        where.append("a.personnel_id = ?")
        params.append(pid)
    if project_filter != "(all)":
        prj_id = project_filter.split("(")[-1].rstrip(")")
        where.append("a.project_id = ?")
        params.append(prj_id)
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY p.full_name, pr.start_period DESC"

    df = db.fetch_df(query, tuple(params))
    if df.empty:
        st.info("No assignments match.")
        return

    st.caption(f"{len(df)} assignments")
    for _, row in df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([3, 4, 2, 2, 1])
        with c1:
            staff_label = row["full_name"]
            if row.get("alias_name"):
                staff_label += f" ({row['alias_name']})"
            st.text(staff_label)
        with c2:
            st.text(f"{row['client_name']} — {row['project_name']}")
        with c3:
            st.text(row["role_on_project"] or "")
        with c4:
            st.caption(row["contribution_notes"] or "")
        with c5:
            if st.button("🗑️", key=f"del_{row['personnel_id']}_{row['project_id']}"):
                db.execute(
                    "DELETE FROM assignments WHERE personnel_id = ? AND project_id = ?",
                    (row["personnel_id"], row["project_id"]),
                )
                st.rerun()


def _render_add_form():
    staff_options = db.fetch_all(
        "SELECT personnel_id, full_name, alias_name FROM personnel WHERE active = 'Yes' ORDER BY full_name"
    )
    project_options = db.fetch_all(
        "SELECT project_id, client_name, project_name FROM projects ORDER BY client_name"
    )

    with st.form("add_assignment"):
        c1, c2 = st.columns(2)
        with c1:
            staff_choice = st.selectbox(
                "Staff",
                [_label(s) for s in staff_options],
            )
        with c2:
            project_choice = st.selectbox(
                "Project",
                [f"{p['client_name']} — {p['project_name']} ({p['project_id']})"
                 for p in project_options],
            )
        c1, c2 = st.columns(2)
        with c1:
            role = st.text_input("Role on project",
                                 placeholder="e.g. Team member, Project Manager")
        with c2:
            notes = st.text_input("Contribution notes (optional)")

        submitted = st.form_submit_button("Add assignment", type="primary")

    if submitted:
        if not staff_choice or not project_choice:
            st.error("Pick both staff and project")
            return
        pid = staff_choice.split("(")[-1].rstrip(")")
        prj_id = project_choice.split("(")[-1].rstrip(")")
        try:
            db.insert("assignments", {
                "personnel_id": pid,
                "project_id": prj_id,
                "role_on_project": role,
                "contribution_notes": notes,
            })
            st.success("Assignment added")
            st.rerun()
        except Exception as e:
            st.error(f"Failed: {e}")


def _label(s) -> str:
    name = s["full_name"]
    if s.get("alias_name"):
        name += f" ({s['alias_name']})"
    return f"{name} ({s['personnel_id']})"

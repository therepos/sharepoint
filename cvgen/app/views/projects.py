"""Projects CRUD page — includes inline team-assignment management."""
from __future__ import annotations

from datetime import date

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

    st.caption(f"{len(df)} projects — tick rows to select, then Edit / Delete")

    display_df = df[["project_id", "client_name", "project_name",
                     "start_period", "end_period", "project_type"]].copy()
    display_df = display_df.rename(columns={
        "project_id": "ID",
        "client_name": "Client",
        "project_name": "Project",
        "start_period": "Start",
        "end_period": "End",
        "project_type": "Type",
    })

    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="projects_table",
    )

    selected_rows = list(event.selection.rows) if event and event.selection else []
    selected_ids = [df.iloc[i]["project_id"] for i in selected_rows]

    c1, c2, c3, _ = st.columns([1, 1.4, 1.4, 4])
    with c1:
        if st.button("Edit", disabled=len(selected_ids) != 1, use_container_width=True):
            st.session_state["edit_project_id"] = selected_ids[0]
            st.rerun()
    with c2:
        if st.button(f"🗑️ Delete selected ({len(selected_ids)})",
                     disabled=not selected_ids, use_container_width=True,
                     key="proj_del_sel_btn"):
            st.session_state["confirm_delete_proj_ids"] = selected_ids
            st.rerun()
    with c3:
        if st.button("🗑️ Delete ALL projects", type="secondary",
                     use_container_width=True, key="proj_del_all_btn"):
            st.session_state["confirm_delete_proj_all"] = True
            st.rerun()

    _render_delete_confirmations()


def _render_delete_confirmations():
    if st.session_state.get("confirm_delete_proj_ids"):
        ids = st.session_state["confirm_delete_proj_ids"]
        st.warning(
            f"Delete {len(ids)} project(s)? This also removes their team assignments (cascade)."
        )
        c1, c2, _ = st.columns([1, 1, 5])
        with c1:
            if st.button("Confirm delete", type="primary", key="proj_del_confirm"):
                for pid in ids:
                    db.delete("projects", "project_id", pid)
                del st.session_state["confirm_delete_proj_ids"]
                st.success(f"Deleted {len(ids)} project(s)")
                st.rerun()
        with c2:
            if st.button("Cancel", key="proj_del_cancel"):
                del st.session_state["confirm_delete_proj_ids"]
                st.rerun()

    if st.session_state.get("confirm_delete_proj_all"):
        st.error(
            "Delete **ALL** projects? This wipes the projects table and cascades to "
            "assignments. This cannot be undone."
        )
        confirm_text = st.text_input(
            "Type DELETE ALL to confirm", key="confirm_delete_proj_all_text"
        )
        c1, c2, _ = st.columns([1, 1, 5])
        with c1:
            if st.button("Confirm wipe", type="primary",
                         disabled=confirm_text != "DELETE ALL",
                         key="proj_wipe_confirm"):
                db.execute("DELETE FROM projects")
                del st.session_state["confirm_delete_proj_all"]
                st.session_state.pop("confirm_delete_proj_all_text", None)
                st.success("All projects deleted")
                st.rerun()
        with c2:
            if st.button("Cancel", key="proj_wipe_cancel"):
                del st.session_state["confirm_delete_proj_all"]
                st.session_state.pop("confirm_delete_proj_all_text", None)
                st.rerun()


# ---------------------------------------------------------------------------
# Edit form
# ---------------------------------------------------------------------------
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

    sector_options = _distinct_tag_values("sector_tags")
    scope_options = _distinct_tag_values("scope_areas")

    with st.form("project_form"):
        c1, c2 = st.columns(2)
        with c1:
            project_id_val = st.text_input("Project ID", value=record["project_id"], disabled=not is_new)
            client_name = st.text_input("Client name", value=record["client_name"])
            project_name = st.text_input("Project name", value=record["project_name"])
            project_type = st.selectbox("Type", PROJECT_TYPES,
                                         index=PROJECT_TYPES.index(record.get("project_type") or "internal_audit"))
        with c2:
            start_period_date = st.date_input(
                "Start period",
                value=_parse_yyyymm(record.get("start_period")) or date.today().replace(day=1),
                format="YYYY-MM-DD",
                help="Day is ignored — only year/month are stored.",
            )
            end_is_present = st.checkbox(
                "End is 'present' (ongoing)",
                value=(record.get("end_period") or "").strip().lower() == "present",
            )
            end_period_date = st.date_input(
                "End period",
                value=_parse_yyyymm(record.get("end_period")) or date.today().replace(day=1),
                format="YYYY-MM-DD",
                disabled=end_is_present,
                help="Ignored when 'present' is ticked.",
            )

            sector_current = _split_csv(record.get("sector_tags"))
            sector_tags_list = st.multiselect(
                "Sector tags",
                options=sorted(set(sector_options) | set(sector_current)),
                default=sector_current,
                help="Pick existing tags. Add new ones via the box below.",
            )
            sector_extra = st.text_input(
                "Add new sector tag(s) (comma-sep)", value="",
                help="Anything you type here is appended to the selected tags.",
            )

            scope_current = _split_csv(record.get("scope_areas"))
            scope_areas_list = st.multiselect(
                "Scope areas",
                options=sorted(set(scope_options) | set(scope_current)),
                default=scope_current,
            )
            scope_extra = st.text_input(
                "Add new scope area(s) (comma-sep)", value="",
            )

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
        merged_sectors = _merge_tags(sector_tags_list, sector_extra)
        merged_scope = _merge_tags(scope_areas_list, scope_extra)
        data = {
            "client_name": client_name, "project_name": project_name,
            "description": description,
            "start_period": _format_yyyymm(start_period_date),
            "end_period": "present" if end_is_present else _format_yyyymm(end_period_date),
            "project_type": project_type,
            "sector_tags": ",".join(merged_sectors),
            "scope_areas": ",".join(merged_scope),
        }
        if is_new:
            data["project_id"] = project_id_val
            db.insert("projects", data)
            st.success(f"Created {project_id_val}")
            st.session_state["edit_project_id"] = project_id_val
        else:
            db.update("projects", "project_id", project_id, data)
            st.success("Saved")
        st.rerun()

    if cancel:
        del st.session_state["edit_project_id"]
        st.rerun()

    if delete_btn:
        db.delete("projects", "project_id", project_id)
        st.success("Deleted")
        del st.session_state["edit_project_id"]
        st.rerun()

    # Inline team management — only for existing projects
    if not is_new:
        st.divider()
        _render_team_section(project_id)


# ---------------------------------------------------------------------------
# Team section (replaces standalone Assignments page)
# ---------------------------------------------------------------------------
def _render_team_section(project_id: str):
    st.markdown("### Team assigned")

    team_df = db.fetch_df(
        """
        SELECT p.personnel_id, p.full_name, p.alias_name,
               a.role_on_project, a.contribution_notes
        FROM assignments a JOIN personnel p ON a.personnel_id = p.personnel_id
        WHERE a.project_id = ?
        ORDER BY p.full_name
        """,
        (project_id,),
    )

    if team_df.empty:
        st.caption("No team assigned yet.")
    else:
        for _, t in team_df.iterrows():
            label = t["full_name"]
            if t.get("alias_name"):
                label += f" ({t['alias_name']})"
            c1, c2, c3, c4 = st.columns([3, 2, 3, 1])
            with c1:
                st.text(f"{label} — {t['personnel_id']}")
            with c2:
                st.text(t["role_on_project"] or "—")
            with c3:
                st.caption(t["contribution_notes"] or "")
            with c4:
                if st.button("Remove", key=f"rm_team_{t['personnel_id']}_{project_id}"):
                    db.execute(
                        "DELETE FROM assignments WHERE personnel_id = ? AND project_id = ?",
                        (t["personnel_id"], project_id),
                    )
                    st.rerun()

    # Add team member
    assigned_ids = set(team_df["personnel_id"]) if not team_df.empty else set()
    available = db.fetch_all(
        "SELECT personnel_id, full_name, alias_name FROM personnel "
        "WHERE active = 'Yes' ORDER BY full_name"
    )
    available = [s for s in available if s["personnel_id"] not in assigned_ids]

    if not available:
        st.caption("All active staff already assigned.")
        return

    with st.form(f"add_team_{project_id}", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            choice = st.selectbox(
                "Add team member",
                [_staff_label(s) for s in available],
                key=f"add_team_choice_{project_id}",
            )
        with c2:
            role = st.text_input("Role on project", value="Team member",
                                  key=f"add_team_role_{project_id}")
        with c3:
            submitted = st.form_submit_button("Add", type="primary",
                                              use_container_width=True)
    if submitted and choice:
        pid = choice.split("(")[-1].rstrip(")")
        try:
            db.insert("assignments", {
                "personnel_id": pid,
                "project_id": project_id,
                "role_on_project": role,
                "contribution_notes": "",
            })
            st.rerun()
        except Exception as e:
            st.error(f"Failed: {e}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _staff_label(s) -> str:
    name = s["full_name"]
    if s.get("alias_name"):
        name += f" ({s['alias_name']})"
    return f"{name} ({s['personnel_id']})"


def _split_csv(val: str | None) -> list[str]:
    if not val:
        return []
    return [t.strip() for t in val.split(",") if t.strip()]


def _merge_tags(selected: list[str], extra_csv: str) -> list[str]:
    extras = _split_csv(extra_csv)
    seen: list[str] = []
    for t in [*selected, *extras]:
        if t and t not in seen:
            seen.append(t)
    return seen


def _distinct_tag_values(column: str) -> list[str]:
    """Pull distinct comma-separated tag values from the projects table."""
    rows = db.fetch_all(f"SELECT DISTINCT {column} AS v FROM projects WHERE {column} IS NOT NULL AND {column} != ''")
    bag: set[str] = set()
    for r in rows:
        for t in _split_csv(r["v"]):
            bag.add(t)
    return sorted(bag)


def _parse_yyyymm(val: str | None) -> date | None:
    """Parse 'YYYY-MM' or 'YYYY-MM-DD' (or 'present') -> date(year, month, 1)."""
    if not val:
        return None
    val = val.strip()
    if val.lower() == "present":
        return None
    parts = val.split("-")
    try:
        if len(parts) >= 2:
            return date(int(parts[0]), int(parts[1]), 1)
    except (ValueError, IndexError):
        return None
    return None


def _format_yyyymm(d: date | None) -> str:
    if not d:
        return ""
    return f"{d.year:04d}-{d.month:02d}"

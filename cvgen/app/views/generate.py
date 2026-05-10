"""Generate Annex E documents."""
from datetime import datetime
from pathlib import Path

import streamlit as st

from app import db
from app.config import OUTPUT_DIR, TEMPLATES_DIR
from app.core.generator import generate_annex_e


def render():
    st.title("Generate Annex E")

    # Step 1: pick template
    templates = sorted(p for p in TEMPLATES_DIR.glob("*.docx")
                       if not p.name.startswith("~") and "_repaired" not in p.name)
    if not templates:
        st.error("No templates available. Upload one on the Templates page first.")
        return
    template_choice = st.selectbox(
        "Template",
        [p.name for p in templates],
    )
    template_path = TEMPLATES_DIR / template_choice

    # Step 2: pick staff
    st.markdown("### Staff to include")
    staff_df = db.fetch_df(
        "SELECT personnel_id, full_name, alias_name, position, department "
        "FROM personnel WHERE active = 'Yes' ORDER BY full_name"
    )
    if staff_df.empty:
        st.info("No active staff.")
        return

    sel_key = "generate_selected_ids"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = set()

    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        if st.button("Select all", use_container_width=True):
            st.session_state[sel_key] = set(staff_df["personnel_id"].tolist())
            st.rerun()
    with c2:
        if st.button("Select none", use_container_width=True):
            st.session_state[sel_key] = set()
            st.rerun()

    display = staff_df[["personnel_id", "full_name", "alias_name", "position", "department"]].rename(
        columns={
            "personnel_id": "ID", "full_name": "Name", "alias_name": "Alias",
            "position": "Position", "department": "Department",
        }
    ).copy()
    display.insert(0, "Include", display["ID"].isin(st.session_state[sel_key]))

    edited = st.data_editor(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Include": st.column_config.CheckboxColumn("Include", default=False),
            "ID": st.column_config.TextColumn("ID", disabled=True),
            "Name": st.column_config.TextColumn("Name", disabled=True),
            "Alias": st.column_config.TextColumn("Alias", disabled=True),
            "Position": st.column_config.TextColumn("Position", disabled=True),
            "Department": st.column_config.TextColumn("Department", disabled=True),
        },
        key="generate_staff_editor",
    )

    selected_ids = edited.loc[edited["Include"], "ID"].tolist()
    st.session_state[sel_key] = set(selected_ids)
    st.caption(f"{len(selected_ids)} of {len(staff_df)} staff selected")

    # Step 3: filters (optional)
    with st.expander("Filters (optional — leave blank for no filter)"):
        c1, c2 = st.columns(2)
        with c1:
            window_start = st.text_input("Project window start (YYYY-MM)", value="2024-04")
            sector_filter = st.text_input("Sector tags (comma)", value="",
                                           help="e.g. government,charity")
        with c2:
            window_end = st.text_input("Project window end (YYYY-MM)", value="2026-03")
            scope_filter = st.text_input("Scope areas (comma)", value="",
                                          help="e.g. procurement,grants")

    if st.button("Generate", type="primary", disabled=not selected_ids):
        if not selected_ids:
            st.error("Pick at least one staff.")
            return

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        sector_tags = [t.strip() for t in sector_filter.split(",") if t.strip()] or None
        scope_tags = [t.strip() for t in scope_filter.split(",") if t.strip()] or None
        window = (window_start, window_end) if window_start and window_end else None

        progress = st.progress(0.0)
        results = []
        for i, pid in enumerate(selected_ids):
            try:
                docx_path, pdf_path = generate_annex_e(
                    template_path=template_path,
                    personnel_id=pid,
                    output_dir=OUTPUT_DIR,
                    sector_tags=sector_tags,
                    scope_areas=scope_tags,
                    date_range=window,
                    timestamp=timestamp,
                )
                results.append((pid, docx_path, pdf_path, None))
            except Exception as e:
                results.append((pid, None, None, str(e)))
            progress.progress((i + 1) / len(selected_ids))

        st.success(f"Generated {sum(1 for r in results if r[1])} of {len(results)}")
        st.caption(f"Output folder: {OUTPUT_DIR}")
        for pid, docx, pdf, err in results:
            person = db.fetch_one("SELECT full_name FROM personnel WHERE personnel_id = ?", (pid,))
            name = person["full_name"] if person else pid
            if err:
                st.error(f"❌ {name}: {err}")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    if docx:
                        with open(docx, "rb") as f:
                            st.download_button(
                                f"📄 {Path(docx).name}",
                                f.read(),
                                file_name=Path(docx).name,
                                key=f"dl_docx_{pid}",
                            )
                with c2:
                    if pdf:
                        with open(pdf, "rb") as f:
                            st.download_button(
                                f"📑 {Path(pdf).name}",
                                f.read(),
                                file_name=Path(pdf).name,
                                key=f"dl_pdf_{pid}",
                            )

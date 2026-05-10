"""Templates page — upload .docx templates, validate placeholders."""
from pathlib import Path

import streamlit as st
from docxtpl import DocxTemplate

from app.config import TEMPLATES_DIR
from app.core.repair import repair_template


# Known placeholder names that the generator can supply
KNOWN_TOP_LEVEL = {
    "full_name", "alias_name", "nationality", "position", "department",
    "role", "start_year", "years", "active", "notes",
    "education", "certifications", "employment", "projects",
    "window_start", "window_end", "generated_at",
}
KNOWN_LOOP_VARS = {"edu", "cert", "emp", "proj"}


def render():
    st.title("Templates")
    st.caption(f"Templates folder: `{TEMPLATES_DIR}`")

    # Upload
    uploaded = st.file_uploader("Upload a Word template (.docx)", type=["docx"])
    if uploaded is not None:
        target = TEMPLATES_DIR / uploaded.name
        target.write_bytes(uploaded.getvalue())
        st.success(f"Saved {uploaded.name}")
        # Validate immediately
        _validate_and_show(target)

    st.divider()

    # List existing
    files = sorted(p for p in TEMPLATES_DIR.glob("*.docx")
                   if not p.name.startswith("~") and "_repaired" not in p.name)
    if not files:
        st.info("No templates uploaded yet.")
        return

    st.subheader(f"Available templates ({len(files)})")
    for f in files:
        with st.expander(f.name):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                size_kb = f.stat().st_size // 1024
                st.caption(f"{size_kb} KB")
            with c2:
                if st.button("Validate", key=f"val_{f.name}"):
                    _validate_and_show(f)
            with c3:
                if st.button("🗑️ Delete", key=f"del_{f.name}", type="secondary"):
                    f.unlink()
                    st.rerun()


def _validate_and_show(template_path: Path):
    """Repair Word-split placeholders and show detected variables."""
    try:
        repaired = repair_template(template_path)
        doc = DocxTemplate(str(repaired))
        placeholders = doc.get_undeclared_template_variables()
    except Exception as e:
        st.error(f"Template syntax error: {e}")
        return

    # Categorize
    top_level = {p for p in placeholders if "." not in p}
    loop_subvars = {p.split(".", 1)[0] for p in placeholders if "." in p}
    unknown_top = top_level - KNOWN_TOP_LEVEL
    unknown_loops = loop_subvars - KNOWN_LOOP_VARS

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Top-level placeholders detected:**")
        for p in sorted(top_level):
            mark = "✅" if p in KNOWN_TOP_LEVEL else "⚠️"
            st.markdown(f"- {mark} `{{{{ {p} }}}}`")
    with c2:
        st.markdown("**Loop variables detected:**")
        for v in sorted(loop_subvars):
            mark = "✅" if v in KNOWN_LOOP_VARS else "⚠️"
            st.markdown(f"- {mark} `{v}` (e.g. `{{{{ {v}.something }}}}`)")

    if unknown_top:
        st.warning(f"Unknown top-level placeholders (won't render): {sorted(unknown_top)}")
    if unknown_loops:
        st.warning(f"Unknown loop variables: {sorted(unknown_loops)}")
    if not unknown_top and not unknown_loops:
        st.success("All placeholders match known fields ✓")

"""Settings & diagnostics."""
import shutil
from datetime import datetime

import streamlit as st

from app import db
from app.config import DATA_DIR, DB_PATH, OUTPUT_DIR, TEMPLATES_DIR, VERSION


def render():
    st.title("Settings")

    st.markdown("### Paths")
    st.code(
        f"DB:        {DB_PATH}\n"
        f"DATA:      {DATA_DIR}\n"
        f"TEMPLATES: {TEMPLATES_DIR}\n"
        f"OUTPUT:    {OUTPUT_DIR}\n"
    )

    st.markdown("### Database stats")
    stats = []
    for tbl in ["personnel", "education", "certifications", "employment",
                "projects", "assignments", "pii", "family"]:
        try:
            count = db.fetch_one(f"SELECT COUNT(*) AS n FROM {tbl}")["n"]
        except Exception:
            count = "—"
        stats.append((tbl, count))
    for name, count in stats:
        c1, c2 = st.columns([2, 1])
        c1.text(name)
        c2.text(str(count))

    st.divider()
    st.markdown("### Backup")
    if st.button("Create backup of personnel.db"):
        backup_name = f"personnel-{datetime.now():%Y%m%d-%H%M%S}.db"
        backup_path = DATA_DIR / backup_name
        shutil.copy2(DB_PATH, backup_path)
        st.success(f"Backed up to {backup_path}")

    backups = sorted(DATA_DIR.glob("personnel-*.db"), reverse=True)
    if backups:
        st.caption(f"{len(backups)} backups in {DATA_DIR}")
        for b in backups[:10]:
            size_kb = b.stat().st_size // 1024
            st.markdown(f"- `{b.name}` ({size_kb} KB)")

    st.divider()
    st.caption(f"cvgen v{VERSION}")

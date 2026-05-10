"""Bulk import — upload CSV/Excel and load into a chosen table."""
from io import BytesIO

import pandas as pd
import streamlit as st

from app import db


TABLES = {
    "personnel": ["personnel_id", "full_name", "alias_name", "nationality",
                  "position", "department", "role", "start_year", "active", "generate", "notes"],
    "education": ["education_id", "personnel_id", "course_name", "institution", "year_attained"],
    "certifications": ["certification_id", "personnel_id", "name", "year_attained"],
    "employment": ["employment_id", "personnel_id", "company", "start_period",
                   "end_period", "designation", "responsibilities"],
    "projects": ["project_id", "client_name", "project_name", "description",
                 "start_period", "end_period", "project_type", "sector_tags", "scope_areas"],
    "assignments": ["personnel_id", "project_id", "role_on_project", "contribution_notes"],
    "pii": ["personnel_id", "nric_passport", "other_id", "pr_status", "fin_holder",
            "citizenship", "place_of_birth", "dob", "designation", "company"],
    "family": ["family_id", "personnel_id", "family_member_name", "relationship",
               "id_type", "id_number", "citizenship", "pr_status", "workpass_holder",
               "gender", "dob", "country_of_birth"],
}

# Columns that are NOT NULL without a default in the schema. Bulk import must
# refuse to insert rows where any of these is unmapped or empty, otherwise
# SQLite raises an opaque NOT NULL constraint failure.
REQUIRED_COLS = {
    "personnel": ["personnel_id", "full_name"],
    "education": ["education_id", "personnel_id", "course_name"],
    "certifications": ["certification_id", "personnel_id", "name"],
    "employment": ["employment_id", "personnel_id", "company"],
    "projects": ["project_id", "client_name", "project_name"],
    "assignments": ["personnel_id", "project_id"],
    "pii": ["personnel_id"],
    "family": ["family_id", "personnel_id", "family_member_name"],
}


def render():
    st.title("Bulk Import")
    st.caption("Upload a CSV or Excel file and load rows into a database table.")

    table = st.selectbox("Target table", list(TABLES.keys()))
    expected_cols = TABLES[table]
    required_cols = REQUIRED_COLS.get(table, [])
    st.markdown(f"**Expected columns:** `{', '.join(expected_cols)}`")
    if required_cols:
        st.markdown(f"**Required (NOT NULL):** `{', '.join(required_cols)}`")

    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
    if not uploaded:
        return

    # Read
    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded, dtype=str, keep_default_na=False)
    else:
        # If multi-sheet, ask which one
        excel = pd.ExcelFile(BytesIO(uploaded.getvalue()))
        if len(excel.sheet_names) > 1:
            sheet = st.selectbox("Sheet", excel.sheet_names)
        else:
            sheet = excel.sheet_names[0]
        df = pd.read_excel(BytesIO(uploaded.getvalue()), sheet_name=sheet,
                            dtype=str, keep_default_na=False)

    st.caption(f"Loaded {len(df)} rows")
    st.dataframe(df.head(10), use_container_width=True)

    # Column mapping
    st.markdown("### Column mapping")
    file_cols = list(df.columns)
    mapping = {}
    for col in expected_cols:
        default = col if col in file_cols else "(skip)"
        mapping[col] = st.selectbox(
            f"{col}",
            ["(skip)"] + file_cols,
            index=(file_cols.index(default) + 1) if default in file_cols else 0,
            key=f"map_{col}",
        )

    mode = st.radio(
        "Import mode",
        ["Insert only (fail on duplicate)", "Insert or replace (upsert)"],
        horizontal=True,
    )

    if st.button("Import", type="primary"):
        unmapped_required = [c for c in required_cols if mapping.get(c) == "(skip)"]
        if unmapped_required:
            st.error(
                f"Required column(s) not mapped: {', '.join(unmapped_required)}. "
                f"Map every NOT NULL column to a source column before importing."
            )
            return

        # Build mapped DataFrame
        rows_to_insert = []
        skipped_missing_required = 0
        for _, row in df.iterrows():
            data = {}
            for col, src in mapping.items():
                if src == "(skip)":
                    continue
                val = row.get(src, "")
                # Strip strings, leave numbers as-is
                if isinstance(val, str):
                    val = val.strip()
                data[col] = val
            if not any(v not in ("", None) for v in data.values()):
                continue
            if any(data.get(c) in ("", None) for c in required_cols):
                skipped_missing_required += 1
                continue
            rows_to_insert.append(data)

        if skipped_missing_required:
            st.warning(
                f"Skipped {skipped_missing_required} row(s) with empty required field(s): "
                f"{', '.join(required_cols)}."
            )

        if not rows_to_insert:
            st.error("No data to import.")
            return

        # Execute
        success = 0
        errors = []
        for r in rows_to_insert:
            try:
                if mode.startswith("Insert or replace"):
                    cols = ", ".join(r.keys())
                    placeholders = ", ".join("?" for _ in r)
                    sql = f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})"
                    db.execute(sql, tuple(r.values()))
                else:
                    db.insert(table, r)
                success += 1
            except Exception as e:
                errors.append((r, str(e)))

        st.success(f"Imported {success} of {len(rows_to_insert)} rows")
        if errors:
            st.error(f"{len(errors)} errors:")
            for r, err in errors[:10]:
                st.markdown(f"- `{r}` → {err}")
            if len(errors) > 10:
                st.caption(f"… and {len(errors) - 10} more")

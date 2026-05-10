"""Excel → SQLite importer. Used for first-time seeding from existing personnel_database.xlsx."""
import sys
from pathlib import Path

import pandas as pd

from app import db
from app.config import DATA_DIR


SHEET_TO_TABLE = {
    "Personnel": "personnel",
    "Education": "education",
    "Certifications": "certifications",
    "Employment": "employment",
    "Projects": "projects",
    "Assignments": "assignments",
    "PII": "pii",
    "Family": "family",
}

# Columns to ignore from Excel (helper columns added for visual lookup)
IGNORE_COLS = {"staff_name", "client_name", "project_name", "years"}


def seed_from_excel(xlsx_path: Path):
    """Read all known sheets from xlsx and insert into SQLite. Replaces existing rows on conflict."""
    sheets = pd.read_excel(xlsx_path, sheet_name=None, dtype=str, keep_default_na=False)
    db.init_db()

    # Order matters: parent tables first
    order = ["personnel", "education", "certifications", "employment",
             "projects", "assignments", "pii", "family"]

    for table in order:
        sheet_name = next((sn for sn, tbl in SHEET_TO_TABLE.items() if tbl == table), None)
        if not sheet_name or sheet_name not in sheets:
            print(f"  skip {table}: no '{sheet_name}' sheet")
            continue

        df = sheets[sheet_name]
        # Drop helper columns
        for col in list(df.columns):
            if col in IGNORE_COLS:
                df = df.drop(columns=[col])

        rows = df.to_dict(orient="records")
        # Filter out empty rows (no PK or all-empty)
        pk_col = _pk_column(table)
        rows = [r for r in rows if r.get(pk_col) or table == "assignments"]

        success = 0
        errors = []
        for r in rows:
            # Convert empty strings to None for nullable cols, strip
            cleaned = {}
            for k, v in r.items():
                if isinstance(v, str):
                    v = v.strip()
                if v == "":
                    v = None
                cleaned[k] = v
            try:
                cols = ", ".join(cleaned.keys())
                placeholders = ", ".join("?" for _ in cleaned)
                sql = f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})"
                db.execute(sql, tuple(cleaned.values()))
                success += 1
            except Exception as e:
                errors.append((cleaned, str(e)))

        print(f"  {table}: {success} ok, {len(errors)} errors")
        for r, err in errors[:5]:
            print(f"    ! {err}: {r}")


def _pk_column(table: str) -> str:
    return {
        "personnel": "personnel_id",
        "education": "education_id",
        "certifications": "certification_id",
        "employment": "employment_id",
        "projects": "project_id",
        "assignments": "personnel_id",
        "pii": "personnel_id",
        "family": "family_id",
    }.get(table, "id")


def main():
    """Entry point: docker compose exec cvgen python -m app.core.importer"""
    if len(sys.argv) > 1:
        xlsx = Path(sys.argv[1])
    else:
        # Look for seed.xlsx in data dir
        xlsx = DATA_DIR / "seed.xlsx"

    if not xlsx.exists():
        print(f"Excel file not found: {xlsx}")
        print("Place your seed file at /app/data/seed.xlsx and run again.")
        sys.exit(1)

    print(f"Importing from {xlsx}...")
    seed_from_excel(xlsx)
    print("Done.")


if __name__ == "__main__":
    main()

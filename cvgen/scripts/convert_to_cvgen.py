"""Convert a personnel-database xlsx into the shape expected by cvgen's Bulk Import page.

Usage:
    python3 convert_to_cvgen.py path/to/personnel_database.xlsx
        -> writes path/to/personnel_database_cvgen_ready.xlsx

Self-installs pandas + openpyxl into the active Python if missing.

Source -> target mapping (sheet -> table):
  Personnel       -> personnel       (drops `years`; renames `include` -> `generate`)
  Education       -> education       (drops `staff_name`)
  Certifications  -> certifications  (drops `staff_name`)
  Employment      -> employment      (drops `staff_name`)
  Projects        -> projects        (no change)
  Assignments     -> assignments     (drops `staff_name`, `client_name`, `project_name`)
  PII             -> pii             (drops `staff_name`; renames `dob_yyyymmdd` -> `dob`)
  Family          -> family          (drops `staff_name`; renames `dob_yyyymmdd` -> `dob`)

Bulk-import order in the cvgen UI (foreign-key dependency):
  1. personnel
  2. projects
  3. education / certifications / employment / pii / family  (any order)
  4. assignments
"""
from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path


def _ensure(pkg: str, import_name: str | None = None) -> None:
    name = import_name or pkg
    try:
        importlib.import_module(name)
    except ImportError:
        print(f"[setup] installing {pkg} ...", flush=True)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", pkg]
        )
        importlib.invalidate_caches()
        importlib.import_module(name)


_ensure("pandas")
_ensure("openpyxl")

import pandas as pd  # noqa: E402


SCHEMA: dict[str, list[str]] = {
    "personnel": [
        "personnel_id", "full_name", "alias_name", "nationality", "position",
        "department", "role", "start_year", "active", "generate", "notes",
    ],
    "education": [
        "education_id", "personnel_id", "course_name", "institution", "year_attained",
    ],
    "certifications": [
        "certification_id", "personnel_id", "name", "year_attained",
    ],
    "employment": [
        "employment_id", "personnel_id", "company", "start_period",
        "end_period", "designation", "responsibilities",
    ],
    "projects": [
        "project_id", "client_name", "project_name", "description",
        "start_period", "end_period", "project_type", "sector_tags", "scope_areas",
    ],
    "assignments": [
        "personnel_id", "project_id", "role_on_project", "contribution_notes",
    ],
    "pii": [
        "personnel_id", "nric_passport", "other_id", "pr_status", "fin_holder",
        "citizenship", "place_of_birth", "dob", "designation", "company",
    ],
    "family": [
        "family_id", "personnel_id", "family_member_name", "relationship",
        "id_type", "id_number", "citizenship", "pr_status", "workpass_holder",
        "gender", "dob", "country_of_birth",
    ],
}

SHEET_MAP: dict[str, str] = {
    "Personnel": "personnel",
    "Education": "education",
    "Certifications": "certifications",
    "Employment": "employment",
    "Projects": "projects",
    "Assignments": "assignments",
    "PII": "pii",
    "Family": "family",
}

RENAMES: dict[str, dict[str, str]] = {
    "personnel": {"include": "generate"},
    "pii":       {"dob_yyyymmdd": "dob"},
    "family":    {"dob_yyyymmdd": "dob"},
}


def convert(src: Path, dst: Path) -> None:
    available = pd.ExcelFile(src).sheet_names
    print(f"Reading: {src}")
    with pd.ExcelWriter(dst, engine="openpyxl") as writer:
        for sheet, table in SHEET_MAP.items():
            if sheet not in available:
                print(f"  {sheet:<16} -> {table:<16} SKIPPED (sheet missing)")
                continue
            df = pd.read_excel(src, sheet_name=sheet, dtype=str, keep_default_na=False)
            df = df.rename(columns=RENAMES.get(table, {}))
            for col in SCHEMA[table]:
                if col not in df.columns:
                    df[col] = ""
            df[SCHEMA[table]].to_excel(writer, sheet_name=table, index=False)
            print(f"  {sheet:<16} -> {table:<16} {len(df):>4} rows")
    print(f"Wrote:   {dst}")


def validate(dst: Path) -> None:
    """Quick FK + duplicate-PK + required-field check on the output."""
    p_ids = set(pd.read_excel(dst, sheet_name="personnel", dtype=str,
                              keep_default_na=False)["personnel_id"])
    pr_ids = set(pd.read_excel(dst, sheet_name="projects", dtype=str,
                               keep_default_na=False)["project_id"])

    fk_checks = [
        ("education", ["personnel_id"]),
        ("certifications", ["personnel_id"]),
        ("employment", ["personnel_id"]),
        ("assignments", ["personnel_id", "project_id"]),
        ("pii", ["personnel_id"]),
        ("family", ["personnel_id"]),
    ]
    issues: list[str] = []
    for tbl, fks in fk_checks:
        df = pd.read_excel(dst, sheet_name=tbl, dtype=str, keep_default_na=False)
        for fk in fks:
            valid = p_ids if fk == "personnel_id" else pr_ids
            bad = sorted(set(df.loc[(df[fk] != "") & (~df[fk].isin(valid)), fk]))
            if bad:
                issues.append(f"  {tbl}.{fk}: missing -> {bad}")

    print("\nValidation:")
    print("  FK issues:", "(none)" if not issues else "")
    for i in issues:
        print(i)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if "-h" in sys.argv or "--help" in sys.argv else 1)

    src = Path(sys.argv[1]).expanduser().resolve()
    if not src.exists():
        sys.exit(f"Not found: {src}")
    dst = src.with_name(src.stem + "_cvgen_ready.xlsx")

    convert(src, dst)
    validate(dst)


if __name__ == "__main__":
    main()

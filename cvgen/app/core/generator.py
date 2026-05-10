"""Generate Annex E: pull data from DB, render template, convert to PDF."""
import re
import subprocess
from datetime import datetime
from pathlib import Path

from docxtpl import DocxTemplate

from app import db
from app.core.repair import repair_template
from app.core.unbold import apply_label_bold_rule


def safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")


def generate_annex_e(
    template_path: Path,
    personnel_id: str,
    output_dir: Path,
    sector_tags: list[str] | None = None,
    scope_areas: list[str] | None = None,
    project_types: list[str] | None = None,
    date_range: tuple[str, str] | None = None,
    timestamp: str | None = None,
) -> tuple[Path, Path | None]:
    """Render a CV for one person. Returns (docx_path, pdf_path or None)."""
    person = db.fetch_one("SELECT * FROM personnel WHERE personnel_id = ?", (personnel_id,))
    if not person:
        raise ValueError(f"Personnel {personnel_id} not found")

    education = db.fetch_all(
        "SELECT * FROM education WHERE personnel_id = ? ORDER BY year_attained DESC",
        (personnel_id,),
    )
    certifications = db.fetch_all(
        "SELECT * FROM certifications WHERE personnel_id = ? ORDER BY year_attained DESC",
        (personnel_id,),
    )
    employment = db.fetch_all(
        "SELECT * FROM employment WHERE personnel_id = ? ORDER BY start_period DESC",
        (personnel_id,),
    )
    projects = _fetch_projects(personnel_id, sector_tags, scope_areas, project_types, date_range)

    # Build context (template placeholders match DB column names exactly)
    context = dict(person)
    if person.get("start_year"):
        context["years"] = datetime.now().year - person["start_year"]
    context["education"] = education
    context["certifications"] = certifications
    context["employment"] = employment
    context["projects"] = [{**p, "index": i + 1} for i, p in enumerate(projects)]
    if date_range:
        context["window_start"] = date_range[0]
        context["window_end"] = date_range[1]
    else:
        context["window_start"] = ""
        context["window_end"] = ""
    context["generated_at"] = datetime.now().strftime("%Y-%m-%d")

    # Repair → render → unbold
    repaired = repair_template(template_path)
    try:
        doc = DocxTemplate(str(repaired))
        doc.render(context)

        ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        name = person.get("alias_name") or person.get("full_name") or personnel_id
        docx_path = output_dir / f"AnnexE_{safe_filename(name)}_{ts}.docx"
        doc.save(str(docx_path))

        apply_label_bold_rule(docx_path)
    finally:
        if repaired != template_path and repaired.exists():
            try:
                repaired.unlink()
            except OSError:
                pass

    pdf_path = _convert_to_pdf(docx_path)
    return docx_path, pdf_path


def _fetch_projects(personnel_id, sector_tags, scope_areas, project_types, date_range):
    rows = db.fetch_all(
        """
        SELECT p.*, a.role_on_project, a.contribution_notes
        FROM assignments a JOIN projects p ON a.project_id = p.project_id
        WHERE a.personnel_id = ?
        ORDER BY p.start_period DESC
        """,
        (personnel_id,),
    )
    out = []
    for r in rows:
        if project_types and r["project_type"] not in project_types:
            continue
        if sector_tags:
            r_sectors = {t.strip() for t in (r["sector_tags"] or "").split(",") if t.strip()}
            if not (set(sector_tags) & r_sectors):
                continue
        if scope_areas:
            r_scopes = {t.strip() for t in (r["scope_areas"] or "").split(",") if t.strip()}
            if not (set(scope_areas) & r_scopes):
                continue
        if date_range and not _project_in_window(r, date_range):
            continue
        out.append(r)
    return out


def _project_in_window(proj, window):
    win_start, win_end = window
    end = "9999-99" if str(proj.get("end_period", "")).lower() == "present" else str(proj.get("end_period", ""))
    start = str(proj.get("start_period", ""))
    return start <= win_end and end >= win_start


def _convert_to_pdf(docx_path: Path) -> Path | None:
    """Use LibreOffice headless for PDF conversion."""
    pdf_path = docx_path.with_suffix(".pdf")
    for lo in ["soffice", "libreoffice", "/usr/bin/soffice"]:
        try:
            r = subprocess.run(
                [lo, "--headless", "--convert-to", "pdf",
                 "--outdir", str(pdf_path.parent), str(docx_path)],
                capture_output=True, timeout=60,
            )
            if r.returncode == 0 and pdf_path.exists():
                return pdf_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None

"""Repair Word templates whose Jinja markers got split across runs by spellcheck."""
import re
import tempfile
from pathlib import Path

from docx import Document


JINJA_RE = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})', re.DOTALL)


def repair_template(template_path: Path) -> Path:
    """
    Word's spellchecker often splits {{ var }} markers across <w:r> runs,
    making them unreadable to docxtpl. This walks paragraphs and merges
    runs whose joint text spans a marker.

    Returns a path in the system temp dir; caller is responsible for cleanup.
    """
    def merge_runs(p):
        runs = p.runs
        if len(runs) < 2:
            return
        full = "".join(r.text for r in runs)
        if not JINJA_RE.search(full):
            return

        offsets, pos = [], 0
        for r in runs:
            offsets.append((pos, pos + len(r.text), r))
            pos += len(r.text)

        needs = False
        for m in JINJA_RE.finditer(full):
            spanning = [r for s, e, r in offsets if not (e <= m.start() or s >= m.end())]
            if len(spanning) > 1:
                needs = True
                break

        if not needs:
            return

        runs[0].text = full
        for r in runs[1:]:
            r.text = ""

    doc = Document(str(template_path))
    for p in doc.paragraphs:
        merge_runs(p)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    merge_runs(p)

    tmpdir = Path(tempfile.gettempdir())
    repaired = tmpdir / (template_path.stem + "_repaired" + template_path.suffix)
    doc.save(str(repaired))
    return repaired

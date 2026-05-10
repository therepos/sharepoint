# INSTRUCTIONS.md — cvgen handoff

This document captures the project state for handoff to Claude Code. Keep it updated as you make changes.

## What this is

A web app for generating CV/Annex E documents (and other Word forms) from a structured database. Replaces a previous Excel-based workflow that became hard to maintain.

## Stack

- **Streamlit** — web UI
- **SQLite** — single-file database, foreign keys enforced
- **docxtpl** — Jinja-style Word template rendering
- **LibreOffice (in container)** — DOCX → PDF conversion
- **Docker** — packaging and deployment
- **GitHub Actions** — auto-builds Docker image on push to main, pushes to GHCR

## Repo layout

```
sharepoint/                              # repo root
├── README.md
├── .gitignore
├── .github/workflows/cvgen.yml          # build → push to ghcr.io/<owner>/cvgen
└── cvgen/                               # this app
    ├── README.md                        # user-facing setup + deploy
    ├── INSTRUCTIONS.md                  # this file
    ├── Dockerfile
    ├── docker-compose.yml               # reference deployment
    ├── requirements.txt
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                      # Streamlit entry, sidebar nav, login gate
    │   ├── config.py                    # paths from env vars
    │   ├── db.py                        # SQLite connection, helpers
    │   ├── pages/
    │   │   ├── staff.py                 # CRUD + per-staff related summaries
    │   │   ├── projects.py              # CRUD + team summary
    │   │   ├── assignments.py           # link staff ↔ projects, friendly form
    │   │   ├── pii.py                   # sensitive PII (separate page)
    │   │   ├── family.py                # ISD CAT2 family records
    │   │   ├── templates.py             # upload/list/validate .docx
    │   │   ├── generate.py              # pick staff + template → render
    │   │   ├── bulk_import.py           # CSV/Excel mass upload
    │   │   └── settings.py              # paths, stats, backup
    │   ├── core/
    │   │   ├── generator.py             # render pipeline
    │   │   ├── repair.py                # fix Word-split Jinja markers
    │   │   ├── unbold.py                # post-render label/value bold rule
    │   │   └── importer.py              # Excel → SQLite seed
    │   └── schema/
    │       └── 001_init.sql             # initial DB schema
    └── tests/
```

## Volume mounts (in production)

| Host | Container | Contents |
|---|---|---|
| `/mnt/sec/apps/cvgen/data` | `/app/data` | `personnel.db`, `output/` (generated docs), backups |
| `/mnt/sec/apps/cvgen/config` | `/app/config` | settings (currently unused, reserved) |
| `/mnt/sec/apps/cvgen/templates` | `/app/templates` | uploaded `.docx` templates |

Stateless image, all persistence in volumes. `docker compose pull && docker compose up -d` for updates.

## Environment variables

| Var | Required | Purpose |
|---|---|---|
| `CVGEN_USERNAME` | optional (default: `admin`) | login username |
| `CVGEN_PASSWORD` | **required** | login password (plain text, set via .env file) |
| `CVGEN_DATA_DIR` | optional | overrides `/app/data` |
| `CVGEN_CONFIG_DIR` | optional | overrides `/app/config` |
| `CVGEN_TEMPLATES_DIR` | optional | overrides `/app/templates` |
| `TZ` | optional | container timezone (e.g. `Asia/Singapore`) |

## Schema (see `app/schema/001_init.sql`)

Core entities:
- **personnel** (PK: personnel_id, e.g. P001)
- **education / certifications / employment** (FK to personnel)
- **projects** (PK: project_id, e.g. PRJ001)
- **assignments** (PK: composite (personnel_id, project_id))
- **pii** (PK: personnel_id, FK to personnel)
- **family** (PK: family_id, FK to personnel)

Foreign keys are ON. Cascade delete: removing a person removes their education, certs, employment, assignments, pii, family.

## Template convention

Word template placeholders match DB column names exactly. e.g. `{{ full_name }}` ↔ `personnel.full_name`.

Loop variables: `edu`, `cert`, `emp`, `proj`. Use either `{%p for ... %}` (paragraph loop) or `{%tr for ... %}` (table-row loop).

Known top-level placeholders the generator supplies:
- All `personnel.*` columns
- `years` (computed from `start_year`)
- `window_start`, `window_end` (date filter passthrough)
- `generated_at`
- Lists: `education`, `certifications`, `employment`, `projects` (each `proj` also has `index`)

When a user uploads a template, the Templates page validates and warns about unknown placeholders.

## First-time data seeding

User has an existing `personnel_database.xlsx` (v4 from the Excel iteration). To migrate:

```bash
docker compose cp personnel_database.xlsx cvgen:/app/data/seed.xlsx
docker compose exec cvgen python -m app.core.importer
```

The importer reads all 8 sheets (Personnel, Education, Certifications, Employment, Projects, Assignments, PII, Family), drops helper columns (`staff_name`, `client_name`, `project_name`, `years`), and inserts via `INSERT OR REPLACE`. Foreign keys are validated.

## Running locally (development)

```bash
cd cvgen
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

mkdir -p data config templates
export CVGEN_DATA_DIR=$(pwd)/data
export CVGEN_CONFIG_DIR=$(pwd)/config
export CVGEN_TEMPLATES_DIR=$(pwd)/templates
export CVGEN_PASSWORD=devpassword

streamlit run app/main.py
```

LibreOffice required locally for PDF conversion (or comment out the `_convert_to_pdf` step temporarily).

## Building Docker image

```bash
cd cvgen
docker build -t cvgen:local .
docker run --rm -p 8501:8501 \
  -e CVGEN_PASSWORD=test \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/templates:/app/templates \
  cvgen:local
```

## Production deploy (Proxmox)

```bash
# One-time:
mkdir -p /mnt/sec/apps/cvgen/{data,config,templates}
cd /mnt/sec/apps/cvgen
curl -O https://raw.githubusercontent.com/therepos/sharepoint/main/cvgen/docker-compose.yml
cat > .env <<EOF
CVGEN_USERNAME=admin
CVGEN_PASSWORD=<your_password>
EOF
docker compose up -d

# Updates:
docker compose pull && docker compose up -d
```

## Backup / restore

**Backup (in-app):** Settings page → Create backup. Writes `personnel-YYYYMMDD-HHMMSS.db` to `/app/data/`.

**Backup (CLI):**
```bash
cp /mnt/sec/apps/cvgen/data/personnel.db \
   /mnt/sec/apps/cvgen/data/personnel-$(date +%F-%H%M%S).db
```

**Restore:**
```bash
docker compose stop cvgen
cp /mnt/sec/apps/cvgen/data/personnel-<timestamp>.db \
   /mnt/sec/apps/cvgen/data/personnel.db
docker compose start cvgen
```

## Project history (context)

Earlier iterations went through:
1. Excel-only with multiple sheets — became hard to maintain
2. Streamlit + Excel — too many file-sync issues
3. Single-file CLI script + Excel — worked but not friendly for multiple users
4. **This iteration: SQLite + Streamlit + Docker** — proper architecture

The seed `personnel_database.xlsx` from iteration 3 has 33 staff, 47 projects, 81 assignments, plus PII + Family records. Use the importer to bring it into SQLite.

## Known issues / TODO

- [ ] **Generate page** — multi-staff selection works but UX could improve (search-as-you-type)
- [ ] **Family page** — view-only. Add CRUD form (mirror PII page pattern)
- [ ] **Education / Certifications / Employment edit pages** — currently only via bulk import. Add inline edit on staff page.
- [ ] **Auth hardening** — currently plaintext password compared. Consider bcrypt-hashed `CVGEN_PASSWORD_HASH` instead. (`bcrypt` already in requirements.)
- [ ] **Template validation** — known placeholder list in `templates.py` is hardcoded. Could derive from schema.
- [ ] **Backup retention** — Settings page lists backups but doesn't auto-delete old ones. Add policy (keep last 30, delete older).
- [ ] **Tests** — `tests/` directory exists but is empty. Add unit tests for `db.py` helpers, `generator.py` filtering, `repair.py` markers.
- [ ] **First-deploy UX** — currently user must manually run importer. Could auto-detect `seed.xlsx` on first startup and offer in UI.

## Things explicitly out of scope (decided)

- **Form filling for security screening templates (AGD, Cat2, NRF)** — discussed, deferred to later phase. Uses same DB but separate scripts/pages per form type.
- **LLM-generated project descriptions** — user generates externally (Copilot, ClaudeCode, etc.) and pastes back. App stores `description` field as-is.
- **Multi-user concurrent editing** — single-user model; SQLite file locking is sufficient.
- **Remote auth (SSO/OAuth)** — single admin password is fine for self-hosted personal/small-team.

## Working with Claude Code

This is the handoff point. Suggested first prompts:
- "Read INSTRUCTIONS.md and confirm you understand the project structure."
- "Run a local dev environment: install deps, init the DB, start streamlit."
- "Help me migrate my existing personnel_database.xlsx — it's at <path>."
- "Add inline education/certifications editing to the Staff page."

Commit conventions: small, focused commits. Branches optional. Tests welcomed but not required for v1.

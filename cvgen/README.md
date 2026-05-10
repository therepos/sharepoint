# cvgen

Web app for generating CVs (e.g. Annex E personnel forms) from a structured database. Streamlit UI, SQLite backend, Docker-deployed.

## Quick start (Proxmox / any Docker host)

```bash
mkdir -p /mnt/sec/apps/cvgen/{data,config,templates}
cd /mnt/sec/apps/cvgen
curl -O https://raw.githubusercontent.com/therepos/sharepoint/main/cvgen/docker-compose.yml
echo "CVGEN_USERNAME=admin" > .env
echo "CVGEN_PASSWORD=your_password_here" >> .env
docker compose up -d
```

Open `http://<host-ip>:8501`.

## Volume mounts

| Host path | Container path | Purpose |
|---|---|---|
| `/mnt/sec/apps/cvgen/data` | `/app/data` | `personnel.db`, generated `output/` |
| `/mnt/sec/apps/cvgen/config` | `/app/config` | `config.yaml`, app settings |
| `/mnt/sec/apps/cvgen/templates` | `/app/templates` | User-uploaded `.docx` templates |

## Features

- Web UI for staff / projects / assignments / PII / family
- Bulk CSV/Excel import with column mapping + foreign key validation
- Template upload — drop a `.docx`, app detects placeholders and warns on issues
- Annex E generation: pick staff + template → DOCX + PDF
- Login required (single admin, env-configured password)
- Backups: `cp /mnt/sec/apps/cvgen/data/personnel.db backup-$(date +%F).db`

## Update

```bash
docker compose pull && docker compose up -d
```

## First-time data seeding

If you have an existing Excel database (`personnel_database.xlsx`):
1. Place it at `/mnt/sec/apps/cvgen/data/seed.xlsx`
2. Run: `docker compose exec cvgen python -m app.scripts.seed_from_excel`
3. Delete `seed.xlsx` after import

## Architecture

- **Streamlit** — web UI
- **SQLite** — single-file database at `/app/data/personnel.db`
- **docxtpl** — Jinja-style templating for Word docs
- **LibreOffice (in image)** — DOCX → PDF conversion

## Development

```bash
cd cvgen
pip install -r requirements.txt
export CVGEN_DATA_DIR=$(pwd)/data
export CVGEN_CONFIG_DIR=$(pwd)/config
export CVGEN_TEMPLATES_DIR=$(pwd)/templates
mkdir -p data config templates
streamlit run app/main.py
```

## Schema

```
personnel       (personnel_id PK, full_name, alias_name, nationality, position,
                 department, role, start_year, active, generate, notes)
education       (education_id PK, personnel_id FK, course_name, institution, year_attained)
certifications  (certification_id PK, personnel_id FK, name, year_attained)
employment      (employment_id PK, personnel_id FK, company, start_period,
                 end_period, designation, responsibilities)
projects        (project_id PK, client_name, project_name, description,
                 start_period, end_period, project_type, sector_tags, scope_areas)
assignments     (personnel_id FK, project_id FK, role_on_project, contribution_notes,
                 PRIMARY KEY (personnel_id, project_id))
pii             (personnel_id FK PK, nric_passport, other_id, pr_status, fin_holder,
                 citizenship, place_of_birth, dob, designation, company)
family          (family_id PK, personnel_id FK, family_member_name, relationship,
                 id_type, id_number, citizenship, pr_status, workpass_holder,
                 gender, dob, country_of_birth)
```

Foreign keys enforced — orphan records impossible.

## Template convention

Word placeholders match DB column names exactly:

| Template | DB column |
|---|---|
| `{{ full_name }}` | personnel.full_name |
| `{{ alias_name }}` | personnel.alias_name |
| `{% for proj in projects %}{{ proj.client_name }}{% endfor %}` | projects.client_name |

Loops: `{%p for ... %}` (paragraph) or `{%tr for ... %}` (table row). See `docxtpl` docs.

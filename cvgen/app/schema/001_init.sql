-- Initial schema for cvgen
-- Idempotent: safe to run on every startup

CREATE TABLE IF NOT EXISTS personnel (
    personnel_id    TEXT PRIMARY KEY,
    full_name       TEXT NOT NULL,
    alias_name      TEXT DEFAULT '',
    nationality     TEXT DEFAULT '',
    position        TEXT DEFAULT '',
    department      TEXT DEFAULT 'Risk Consulting',
    role            TEXT DEFAULT '',
    start_year      INTEGER,
    active          TEXT DEFAULT 'Yes',
    generate        TEXT DEFAULT 'No',
    notes           TEXT DEFAULT '',
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS education (
    education_id    TEXT PRIMARY KEY,
    personnel_id    TEXT NOT NULL,
    course_name     TEXT NOT NULL,
    institution     TEXT DEFAULT '',
    year_attained   INTEGER,
    FOREIGN KEY (personnel_id) REFERENCES personnel(personnel_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS certifications (
    certification_id TEXT PRIMARY KEY,
    personnel_id    TEXT NOT NULL,
    name            TEXT NOT NULL,
    year_attained   INTEGER,
    FOREIGN KEY (personnel_id) REFERENCES personnel(personnel_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS employment (
    employment_id   TEXT PRIMARY KEY,
    personnel_id    TEXT NOT NULL,
    company         TEXT NOT NULL,
    start_period    TEXT DEFAULT '',
    end_period      TEXT DEFAULT '',
    designation     TEXT DEFAULT '',
    responsibilities TEXT DEFAULT '',
    FOREIGN KEY (personnel_id) REFERENCES personnel(personnel_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projects (
    project_id      TEXT PRIMARY KEY,
    client_name     TEXT NOT NULL,
    project_name    TEXT NOT NULL,
    description     TEXT DEFAULT '',
    start_period    TEXT DEFAULT '',
    end_period      TEXT DEFAULT '',
    project_type    TEXT DEFAULT 'internal_audit',
    sector_tags     TEXT DEFAULT '',
    scope_areas     TEXT DEFAULT '',
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assignments (
    personnel_id        TEXT NOT NULL,
    project_id          TEXT NOT NULL,
    role_on_project     TEXT DEFAULT '',
    contribution_notes  TEXT DEFAULT '',
    PRIMARY KEY (personnel_id, project_id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(personnel_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id)   REFERENCES projects(project_id)   ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pii (
    personnel_id    TEXT PRIMARY KEY,
    nric_passport   TEXT DEFAULT '',
    other_id        TEXT DEFAULT '',
    pr_status       TEXT DEFAULT '',
    fin_holder      TEXT DEFAULT '',
    citizenship     TEXT DEFAULT '',
    place_of_birth  TEXT DEFAULT '',
    dob             TEXT DEFAULT '',
    designation     TEXT DEFAULT '',
    company         TEXT DEFAULT '',
    FOREIGN KEY (personnel_id) REFERENCES personnel(personnel_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS family (
    family_id       TEXT PRIMARY KEY,
    personnel_id    TEXT NOT NULL,
    family_member_name TEXT NOT NULL,
    relationship    TEXT DEFAULT '',
    id_type         TEXT DEFAULT '',
    id_number       TEXT DEFAULT '',
    citizenship     TEXT DEFAULT '',
    pr_status       TEXT DEFAULT '',
    workpass_holder TEXT DEFAULT '',
    gender          TEXT DEFAULT '',
    dob             TEXT DEFAULT '',
    country_of_birth TEXT DEFAULT '',
    FOREIGN KEY (personnel_id) REFERENCES personnel(personnel_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_education_personnel ON education(personnel_id);
CREATE INDEX IF NOT EXISTS idx_certifications_personnel ON certifications(personnel_id);
CREATE INDEX IF NOT EXISTS idx_employment_personnel ON employment(personnel_id);
CREATE INDEX IF NOT EXISTS idx_assignments_project ON assignments(project_id);
CREATE INDEX IF NOT EXISTS idx_family_personnel ON family(personnel_id);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    country TEXT,
    website TEXT,
    total_jobs INTEGER DEFAULT 0,
    active_jobs INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    remote TEXT,
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    published_at TEXT,
    updated_at TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    description TEXT,
    hash TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT REFERENCES jobs(id),
    date TEXT NOT NULL,
    change_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    diff TEXT
);

CREATE TABLE IF NOT EXISTS skills (
    job_id TEXT REFERENCES jobs(id),
    skill TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    PRIMARY KEY (job_id, skill)
);

CREATE TABLE IF NOT EXISTS job_sources (
    job_id TEXT REFERENCES jobs(id),
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    PRIMARY KEY (job_id, source, source_url)
);

CREATE TABLE IF NOT EXISTS source_health (
    source_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_url TEXT,
    status TEXT NOT NULL,
    last_success_at TEXT,
    last_failure_at TEXT,
    last_error TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    avg_response_ms INTEGER,
    avg_jobs_count REAL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    runtime_seconds REAL NOT NULL,
    sources_total INTEGER,
    sources_healthy INTEGER,
    sources_failed INTEGER,
    new_jobs INTEGER,
    updated_jobs INTEGER,
    closed_jobs INTEGER,
    reopened_jobs INTEGER,
    actionable_jobs INTEGER,
    duplicates_removed INTEGER,
    quality_warnings INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS run_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES run_metrics(id),
    job_id TEXT REFERENCES jobs(id),
    activity_type TEXT NOT NULL,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    change_summary TEXT,
    diff TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES jobs(id),
    fit_score INTEGER NOT NULL,
    apply_priority TEXT NOT NULL,
    recommended_resume TEXT,
    prefilter_score INTEGER,
    analysis_json TEXT NOT NULL,
    job_content_hash TEXT NOT NULL,
    candidate_profile_hash TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    analyzed_at TEXT NOT NULL,
    UNIQUE(job_id, job_content_hash, candidate_profile_hash, prompt_version, model)
);

CREATE TABLE IF NOT EXISTS application_packs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT REFERENCES jobs(id),
    activity_type TEXT NOT NULL,
    match_score INTEGER,
    match_strong TEXT,
    match_missing TEXT,
    resume_version TEXT,
    cover_letter TEXT,
    job_analysis_id INTEGER REFERENCES job_analysis(id),
    detected_at TEXT NOT NULL,
    pack_ready_at TEXT NOT NULL,
    time_to_ready_seconds REAL,
    notified_at TEXT
);

CREATE TABLE IF NOT EXISTS recruiters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT,
    linkedin_url TEXT,
    email TEXT,
    first_seen_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT REFERENCES jobs(id),
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    recruiter_id INTEGER REFERENCES recruiters(id),
    applied_at TEXT NOT NULL,
    source TEXT NOT NULL,
    resume_version TEXT,
    cover_letter TEXT,
    stage TEXT DEFAULT 'applied',
    follow_up_at TEXT,
    rejection_reason TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interview_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER REFERENCES applications(id),
    company TEXT NOT NULL,
    date TEXT NOT NULL,
    round TEXT,
    questions TEXT,
    stack_mentioned TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watch_alerts (
    company TEXT PRIMARY KEY,
    alerted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    period TEXT PRIMARY KEY,
    new_jobs INTEGER NOT NULL,
    closed_jobs INTEGER NOT NULL,
    active_jobs INTEGER NOT NULL,
    remote_count INTEGER DEFAULT 0,
    hybrid_count INTEGER DEFAULT 0,
    onsite_count INTEGER DEFAULT 0,
    avg_lifetime_days REAL,
    new_companies INTEGER DEFAULT 0,
    top_hirers_json TEXT,
    skill_trends_json TEXT,
    created_at TEXT NOT NULL
);

-- Culture Desk v0.1. Applications must enable foreign_keys for every connection.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    homepage_url TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('official', 'media', 'demo')),
    access_status TEXT NOT NULL DEFAULT 'unverified' CHECK (access_status IN ('unverified', 'reviewed')),
    access_method TEXT CHECK (access_method IN ('rss', 'api', 'public_page', 'manual', 'demo')),
    verified_at TEXT,
    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    notes TEXT,
    CHECK (enabled = 0 OR (access_status = 'reviewed' AND verified_at IS NOT NULL AND access_method IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS content (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    canonical_url TEXT NOT NULL UNIQUE,
    title_original TEXT NOT NULL,
    title_zh TEXT,
    summary_zh TEXT,
    channel TEXT NOT NULL CHECK (channel IN ('film', 'art', 'photography')),
    kind TEXT NOT NULL CHECK (kind IN ('news', 'interview', 'work', 'photobook', 'industry_buzz')),
    country TEXT,
    city TEXT,
    language TEXT NOT NULL,
    evidence_status TEXT NOT NULL CHECK (evidence_status IN ('official_confirmed', 'media_reported', 'firsthand_response', 'unverified')),
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    summary_status TEXT NOT NULL DEFAULT 'pending' CHECK (summary_status IN ('pending', 'ready', 'failed', 'disabled')),
    summary_provider TEXT,
    summary_model TEXT,
    summary_generated_at TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title_original TEXT NOT NULL,
    title_zh TEXT,
    channel TEXT NOT NULL CHECK (channel IN ('film', 'art', 'photography')),
    event_type TEXT NOT NULL CHECK (event_type IN ('cinema_release', 'festival_screening', 'streaming_release', 'exhibition', 'call_deadline')),
    country TEXT NOT NULL,
    city TEXT,
    venue TEXT,
    start_date TEXT,
    end_date TEXT,
    date_precision TEXT NOT NULL CHECK (date_precision IN ('day', 'month', 'unknown')),
    date_text_original TEXT,
    timezone TEXT NOT NULL,
    price_text TEXT,
    closure_note TEXT,
    booking_url TEXT,
    evidence_url TEXT NOT NULL,
    evidence_status TEXT NOT NULL CHECK (evidence_status IN ('official_confirmed', 'media_reported', 'firsthand_response', 'unverified')),
    verified_at TEXT,
    updated_at TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
    CHECK (country != 'JP' OR timezone = 'Asia/Tokyo'),
    CHECK (date_precision != 'day' OR (start_date IS NOT NULL AND length(start_date) = 10)),
    CHECK (date_precision != 'month' OR (start_date IS NOT NULL AND length(start_date) = 7)),
    CHECK (date_precision != 'unknown' OR (start_date IS NULL AND end_date IS NULL)),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS content_events (
    content_id TEXT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    PRIMARY KEY (content_id, event_id)
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id TEXT PRIMARY KEY,
    content_id TEXT REFERENCES content(id) ON DELETE CASCADE,
    event_id TEXT REFERENCES events(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('want_to_see', 'planning', 'seen')),
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK ((content_id IS NOT NULL AND event_id IS NULL) OR (content_id IS NULL AND event_id IS NOT NULL)),
    UNIQUE (content_id),
    UNIQUE (event_id)
);

CREATE TABLE IF NOT EXISTS ingest_runs (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    fetched_count INTEGER NOT NULL DEFAULT 0 CHECK (fetched_count >= 0),
    inserted_count INTEGER NOT NULL DEFAULT 0 CHECK (inserted_count >= 0),
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_content_filter ON content(channel, kind, country, city);
CREATE INDEX IF NOT EXISTS idx_content_published ON content(published_at);
CREATE INDEX IF NOT EXISTS idx_events_dates ON events(country, city, start_date, end_date);

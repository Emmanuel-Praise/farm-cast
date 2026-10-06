CREATE TABLE IF NOT EXISTS localities (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL,
  aliases       TEXT,
  division      TEXT,
  lat           REAL NOT NULL,
  lon           REAL NOT NULL,
  elevation_m   INTEGER,
  elev_source   TEXT DEFAULT 'seed-estimate', -- 'seed-estimate' | 'geocoding-api' | 'gps'
  manual_bias   REAL DEFAULT 1.0,
  source        TEXT,
  verified      INTEGER DEFAULT 0,
  created_at    TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_loc_name ON localities(name);

CREATE TABLE IF NOT EXISTS farmers (
  id            INTEGER PRIMARY KEY,
  phone         TEXT UNIQUE NOT NULL,
  name          TEXT,
  locality_id   INTEGER REFERENCES localities(id),
  lat           REAL,
  lon           REAL,
  elevation_m   INTEGER,
  crop          TEXT,
  language      TEXT DEFAULT 'english',
  channel       TEXT DEFAULT 'whatsapp',
  active        INTEGER DEFAULT 1,
  created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS forecasts (
  id            INTEGER PRIMARY KEY,
  locality_id   INTEGER REFERENCES localities(id),
  run_date      TEXT,
  p24 REAL, p48 REAL, p72 REAL,
  prob_max REAL, tmin REAL, tmax REAL,
  wind_max REAL, dry_run INTEGER,
  category      TEXT,
  flags         TEXT,
  raw_json      TEXT,
  UNIQUE(locality_id, run_date)
);

CREATE TABLE IF NOT EXISTS messages (
  id            INTEGER PRIMARY KEY,
  farmer_id     INTEGER REFERENCES farmers(id),
  forecast_id   INTEGER REFERENCES forecasts(id),
  kind          TEXT,
  channel       TEXT DEFAULT 'whatsapp',
  text_body     TEXT,
  audio_key     TEXT,
  status        TEXT,
  error         TEXT,
  sent_at       TEXT
);

CREATE TABLE IF NOT EXISTS reports (
  id              INTEGER PRIMARY KEY,
  farmer_id       INTEGER REFERENCES farmers(id),
  locality_id     INTEGER REFERENCES localities(id),
  asked_for_date  TEXT,
  reply           TEXT,
  raw_text        TEXT,
  received_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS queries (
  id                  INTEGER PRIMARY KEY,
  farmer_id           INTEGER REFERENCES farmers(id),
  raw_text            TEXT,
  intent              TEXT,
  resolved_locality_id INTEGER REFERENCES localities(id),
  response            TEXT,
  answered_at         TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pending_clarifications (
  id            INTEGER PRIMARY KEY,
  farmer_id     INTEGER REFERENCES farmers(id),
  options       TEXT,
  expires_at    TEXT
);

CREATE TABLE IF NOT EXISTS call_list (
  id            INTEGER PRIMARY KEY,
  farmer_id     INTEGER REFERENCES farmers(id),
  reason        TEXT,
  created_at    TEXT DEFAULT (datetime('now')),
  resolved      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS onboarding (
  phone         TEXT PRIMARY KEY,
  step          TEXT,              -- 'name' | 'location'
  name          TEXT,
  options       TEXT,              -- JSON locality options when place was ambiguous
  created_at    TEXT DEFAULT (datetime('now'))
);

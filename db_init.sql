CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_id INTEGER UNIQUE NOT NULL,
  chat_id INTEGER NOT NULL,
  city TEXT,
  lat REAL,
  lon REAL,
  timezone TEXT,        -- например "Europe/Moscow"
  tz_offset INTEGER,    -- смещение в секундах от UTC (опционально)
  notify_morning INTEGER DEFAULT 1,
  last_notify_date TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS weather_samples (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_id INTEGER,
  date TEXT,            -- YYYY-MM-DD — день прогноза
  temp REAL,
  temp_max REAL,
  temp_min REAL,
  condition TEXT,       -- e.g. "Clear","Rain","Snow"
  precipitation_type TEXT, -- "rain","snow","none"
  pop REAL,             -- вероятность осадков
  raw_json TEXT,
  fetched_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_weather_tg_date ON weather_samples(tg_id, date);

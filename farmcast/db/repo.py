"""All DB queries. SQLite, stdlib only."""
from __future__ import annotations
import csv
import json
import os
import sqlite3
from datetime import date, datetime, timedelta

try:
    from config import settings
except ImportError:
    from farmcast.config import settings


def connect(path: str | None = None) -> sqlite3.Connection:
    path = path or settings.DATABASE_PATH
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def init_db(path: str | None = None, schema_path: str | None = None):
    path = path or settings.DATABASE_PATH
    if schema_path is None:
        base = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(base, "schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        sql = f.read()
    con = connect(path)
    con.executescript(sql)
    con.commit()
    con.close()


def seed_localities(path: str | None = None, csv_path: str | None = None) -> int:
    path = path or settings.DATABASE_PATH
    if csv_path is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base, "config", "localities_seed.csv")
    con = connect(path)
    n = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cur = con.execute("SELECT id FROM localities WHERE lower(name)=lower(?)",
                              (row["name"].strip(),)).fetchone()
            if cur:
                continue
            con.execute(
                "INSERT INTO localities(name,aliases,division,lat,lon,elevation_m,"
                "source,verified) VALUES(?,?,?,?,?,?,?,?)",
                (row["name"].strip(), row.get("aliases") or "",
                 row.get("division") or "", float(row["lat"]), float(row["lon"]),
                 int(float(row.get("elevation_m") or 0)), "curated", 1))
            n += 1
    con.commit()
    con.close()
    return n


def get_or_create_locality(name: str, lat: float, lon: float, elev: int = 0,
                           division: str = "", source: str = "geocoded",
                           path: str | None = None) -> int:
    con = connect(path)
    row = con.execute(
        "SELECT id FROM localities WHERE ABS(lat-?)<1e-6 AND ABS(lon-?)<1e-6",
        (lat, lon)).fetchone()
    if row:
        con.close()
        return row["id"]
    cur = con.execute(
        "INSERT INTO localities(name,division,lat,lon,elevation_m,source,verified)"
        " VALUES(?,?,?,?,?,?,?)",
        (name, division, lat, lon, elev, source, 0))
    lid = cur.lastrowid
    con.commit()
    con.close()
    return lid


def find_locality_by_name(name: str, path: str | None = None):
    con = connect(path)
    row = con.execute("SELECT * FROM localities WHERE lower(name)=lower(?)",
                      (name.strip(),)).fetchone()
    con.close()
    return dict(row) if row else None


def active_farmers_grouped(path: str | None = None) -> dict[int, list[dict]]:
    """locality_id -> [farmer rows]."""
    con = connect(path)
    rows = con.execute(
        """SELECT f.*, l.name AS locality_name, l.lat AS loc_lat, l.lon AS loc_lon,
                  l.elevation_m AS loc_elev
           FROM farmers f JOIN localities l ON l.id=f.locality_id
           WHERE f.active=1""").fetchall()
    con.close()
    groups: dict[int, list[dict]] = {}
    for r in rows:
        d = dict(r)
        groups.setdefault(d["locality_id"], []).append(d)
    return groups


def find_farmer_by_phone(phone: str, path: str | None = None):
    con = connect(path)
    row = con.execute("SELECT * FROM farmers WHERE phone=?", (phone,)).fetchone()
    con.close()
    return dict(row) if row else None


def save_forecast(locality_id: int, run_date: str, fc, category: str,
                  flags: list[str], path: str | None = None) -> int:
    import json as _json
    con = connect(path)
    raw = _json.dumps(getattr(fc, "raw", None) or {})[:20000] if False else _json.dumps(fc.raw or {})
    con.execute(
        """INSERT INTO forecasts(locality_id,run_date,p24,p48,p72,prob_max,tmin,
               tmax,wind_max,dry_run,category,flags,raw_json)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(locality_id,run_date) DO UPDATE SET
             p24=excluded.p24,p48=excluded.p48,p72=excluded.p72,
             prob_max=excluded.prob_max,tmin=excluded.tmin,tmax=excluded.tmax,
             wind_max=excluded.wind_max,dry_run=excluded.dry_run,
             category=excluded.category,flags=excluded.flags,raw_json=excluded.raw_json""",
        (locality_id, run_date, fc.p24, fc.p48, fc.p72, fc.prob_max, fc.tmin,
         fc.tmax, fc.wind_max, fc.dry_run, category, _json.dumps(flags), raw))
    row = con.execute("SELECT id FROM forecasts WHERE locality_id=? AND run_date=?",
                      (locality_id, run_date)).fetchone()
    con.commit()
    con.close()
    return row["id"]


def log_message(farmer_id: int, forecast_id: int | None, kind: str,
                text_body: str, status: str, error: str = "",
                path: str | None = None):
    con = connect(path)
    con.execute(
        "INSERT INTO messages(farmer_id,forecast_id,kind,channel,text_body,status,"
        "error,sent_at) VALUES(?,?,?,?,?,?,?,?)",
        (farmer_id, forecast_id, kind, "whatsapp", text_body, status, error,
         datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()


def add_to_call_list(farmer_id: int, reason: str, path: str | None = None):
    con = connect(path)
    con.execute("INSERT INTO call_list(farmer_id,reason) VALUES(?,?)",
                (farmer_id, reason))
    con.commit()
    con.close()


def stats(path: str | None = None) -> dict:
    con = connect(path)
    today = date.today().isoformat()
    farmers = con.execute("SELECT COUNT(*) c FROM farmers WHERE active=1").fetchone()["c"]
    locs = con.execute("SELECT COUNT(*) c FROM localities").fetchone()["c"]
    reports = con.execute("SELECT COUNT(*) c FROM reports WHERE date(received_at)=date('now')").fetchone()["c"]
    sent = con.execute("SELECT COUNT(*) c FROM messages WHERE date(sent_at)=date('now')"
                       " AND status IN ('sent','mocked','delivered')").fetchone()["c"]
    failed = con.execute("SELECT COUNT(*) c FROM messages WHERE date(sent_at)=date('now')"
                         " AND status='failed'").fetchone()["c"]
    call = con.execute("SELECT COUNT(*) c FROM call_list WHERE resolved=0").fetchone()["c"]
    per_loc = con.execute(
        """SELECT l.name, l.division, COUNT(f.id) n FROM localities l
           LEFT JOIN farmers f ON f.locality_id=l.id AND f.active=1
           GROUP BY l.id ORDER BY n DESC LIMIT 50""").fetchall()
    recent_reports = con.execute(
        """SELECT r.*, f.name farmer_name FROM reports r
           LEFT JOIN farmers f ON f.id=r.farmer_id
           ORDER BY r.id DESC LIMIT 20""").fetchall()
    recent_msgs = con.execute(
        "SELECT * FROM messages ORDER BY id DESC LIMIT 20").fetchall()
    con.close()
    return {
        "farmers": farmers, "localities": locs, "reports_today": reports,
        "sent_today": sent, "failed_today": failed, "call_list_open": call,
        "per_locality": [dict(x) for x in per_loc],
        "recent_reports": [dict(x) for x in recent_reports],
        "recent_messages": [dict(x) for x in recent_msgs],
        "date": today,
    }

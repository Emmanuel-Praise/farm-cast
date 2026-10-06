"""Morning broadcast: load farmers -> group by locality -> batch fetch -> rules -> send.

Usage: python -m farmcast.broadcast --dry-run
Cron: 05:30 Africa/Douala (fetch+queue), sends stamped 06:00.
Text-only WhatsApp, no SMS.
"""
from __future__ import annotations
import json
from datetime import date

from farmcast.db import repo
from farmcast.core.weather import fetch_places
from farmcast.core import rules as R
from farmcast.core.message import render_broadcast, load_templates
from farmcast.core.channels.whatsapp import send_text


def run(dry_run: bool = False, run_date: str | None = None) -> dict:
    run_date = run_date or date.today().isoformat()
    groups = repo.active_farmers_grouped()
    if not groups:
        print("No active farmers.")
        return {"localities": 0, "farmers": 0, "sent": 0, "failed": 0}

    con = repo.connect()
    locs = {r["id"]: dict(r) for r in
            con.execute(f"SELECT * FROM localities WHERE id IN "
                        f"({','.join('?' * len(groups))})", list(groups)).fetchall()}
    con.close()

    places = []
    for lid, farmers in groups.items():
        L = locs[lid]
        # farm GPS overrides village centre if present (use first farmer's GPS if set)
        f0 = farmers[0]
        lat = f0.get("lat") or L["lat"]
        lon = f0.get("lon") or L["lon"]
        elev = f0.get("elevation_m") or L["elevation_m"] or 0
        places.append({"key": str(lid), "lat": lat, "lon": lon, "elev": elev})
    forecasts = fetch_places(places)

    sent = failed = n_farmers = 0
    t = load_templates("english")
    for lid, farmers in groups.items():
        L = locs[lid]
        fc = forecasts[str(lid)]
        bias = L.get("manual_bias") or 1.0
        p48 = round(fc.p48 * bias, 1)
        p24 = round(fc.p24 * bias, 1)
        cat = R.categorize(p48, fc.daily or [])
        fl = R.flags(fc.tmin, L.get("elevation_m") or 0, fc.wind_max, p48, p24)
        fid = repo.save_forecast(lid, run_date, fc, cat, fl)
        plant_day = R.day_label(R.next_good_plant_day(fc.daily or []))
        for f in farmers:
            n_farmers += 1
            body = render_broadcast(f.get("name") or "farmer", L["name"],
                                    cat, p48, f.get("crop") or "maize",
                                    {"flags": fl, "plant_day": plant_day},
                                    f.get("language") or "english")
            if L.get("lat") and False:  # placeholder for outside-NW note
                pass
            if dry_run:
                print(f"[DRY {L['name']}->{f['phone']}] {body[:160]}...")
                repo.log_message(f["id"], fid, "broadcast", body, "mocked")
                sent += 1
                continue
            res = send_text(f["phone"], body)
            if res.get("ok"):
                repo.log_message(f["id"], fid, "broadcast", body,
                                 res.get("status", "sent"))
                sent += 1
            else:
                repo.log_message(f["id"], fid, "broadcast", body, "failed",
                                 res.get("error", ""))
                failed += 1
    summary = {"localities": len(groups), "farmers": n_farmers,
               "sent": sent, "failed": failed, "date": run_date}
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    run(dry_run=a.dry_run, run_date=a.date)

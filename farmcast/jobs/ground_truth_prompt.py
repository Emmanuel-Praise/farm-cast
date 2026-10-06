"""Ground-truth prompt: queue next-day YES/NO ask for every farmer messaged yesterday."""
from __future__ import annotations
from farmcast.db import repo
from farmcast.core.message import load_templates
from farmcast.core.channels.whatsapp import send_text


def run(dry_run: bool = False) -> dict:
    t = load_templates("english")
    ask = t.get("ground_truth_ask", "Did it rain at your farm yesterday? Reply YES or NO.")
    con = repo.connect()
    farmers = con.execute(
        """SELECT DISTINCT f.* FROM farmers f JOIN messages m ON m.farmer_id=f.id
           WHERE m.kind='broadcast' AND date(m.sent_at)=date('now','-1 day')
           AND f.active=1""").fetchall()
    con.close()
    n = 0
    for f in farmers:
        f = dict(f)
        n += 1
        if dry_run:
            print(f"[DRY ground-truth -> {f['phone']}] {ask}")
            continue
        res = send_text(f["phone"], ask)
        repo.log_message(f["id"], None, "ground_truth_ask", ask,
                         res.get("status", "sent") if res.get("ok") else "failed",
                         "" if res.get("ok") else res.get("error", ""))
    print({"asked": n})
    return {"asked": n}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    run(dry_run=ap.parse_args().dry_run)

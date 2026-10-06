"""Retry queue: retry failed WhatsApp sends once, else add to call list (no SMS)."""
from __future__ import annotations
from farmcast.db import repo
from farmcast.core.channels.whatsapp import send_text


def run(dry_run: bool = False) -> dict:
    con = repo.connect()
    rows = con.execute(
        """SELECT m.*, f.phone FROM messages m JOIN farmers f ON f.id=m.farmer_id
           WHERE m.status='failed' AND date(m.sent_at)=date('now')""").fetchall()
    con.close()
    retried = sent = escalated = 0
    for r in rows:
        r = dict(r)
        retried += 1
        if dry_run:
            print(f"[DRY retry {r['phone']}] {r['text_body'][:120]}...")
            continue
        res = send_text(r["phone"], r["text_body"])
        con2 = repo.connect()
        if res.get("ok"):
            con2.execute("UPDATE messages SET status=?, error='' WHERE id=?",
                         (res.get("status", "sent"), r["id"]))
            sent += 1
        else:
            con2.execute("UPDATE messages SET error=? WHERE id=?",
                         (res.get("error", ""), r["id"]))
            repo.add_to_call_list(r["farmer_id"], "whatsapp_failed_after_retry")
            escalated += 1
        con2.commit()
        con2.close()
    out = {"retried": retried, "sent": sent, "escalated_to_call_list": escalated}
    print(out)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    run(dry_run=ap.parse_args().dry_run)

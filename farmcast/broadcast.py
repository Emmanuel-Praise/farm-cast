"""CLI shim: python -m farmcast.broadcast --dry-run"""
from farmcast.jobs.morning_broadcast import run

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    run(dry_run=a.dry_run, run_date=a.date)

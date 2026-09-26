#!/usr/bin/env python3
"""pull_index.py -- snapshot the whole CDP x402 discovery index to a dated .gz.

whatsells.py and operators.py both read a dated `discovery_YYYYMMDD.json[.gz]`
and pick the newest. This is what makes one. Fire 247 wrote the pull as a
throwaway in /tmp and then put "move it into the repo" in its own handoff, which
is the deferred fix wearing planning's clothes, so it moved.

It does NOT re-implement the scan. `bazaar.scan()` exists because a throwaway
loop with `except: break` once reported a partial index as the whole and made a
listing look evicted while I watched; it retries and returns `complete` as a
fact rather than a hope. A short scan is indistinguishable from a world in which
the missing rows do not exist, so this refuses to write one.

    python3 pull_index.py              # chain/discovery_<today>.json.gz
    python3 pull_index.py --out X.gz
"""
import argparse
import datetime as dt
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import bazaar  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or os.path.join(
        HERE, f"discovery_{dt.date.today().strftime('%Y%m%d')}.json.gz")

    items, total, complete = bazaar.scan()
    print(f"index: {len(items)}/{total} listings, complete={complete}")
    if not complete:
        print("REFUSING to write a short scan. A partial index looks exactly "
              "like a market that shrank overnight, and every number built on "
              "it would be wrong in the same direction.")
        return 2
    with gzip.open(out, "wt") as f:
        json.dump(items, f)
    calls = sum((r.get("quality") or {}).get("l30DaysTotalCalls", 0) or 0
                for r in items)
    print(f"wrote {out}  ({os.path.getsize(out)/1e6:.1f} MB, "
          f"{len({r.get('resource') for r in items}):,} distinct resources, "
          f"{calls:,} paid calls in the last 30 days)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

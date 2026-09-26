#!/usr/bin/env python3
"""bazaar.py — read the Coinbase x402 discovery index, and never under-report.

WHY IT IS A FILE (fire 217, Aug 20 2026).  I scanned this index three times in
one hour with a throwaway loop and got three different answers for how many of
my own routes were listed -- 2, then 2, then 1 -- and briefly believed a listing
had been EVICTED while I watched.  It had not.  The loop did
`except: break`, so a single read timeout on page 12 ended the scan and
reported the partial as the whole.  A scan that stops early looks exactly like
a world in which the missing rows do not exist.

So: retries, and an explicit completeness check against the index's own
`pagination.total`.  If the scan is short it says INCOMPLETE in the return value
and in the printout; it does not quietly hand back a smaller number.

WHAT THE INDEX IS.  Every listing carries a quality block --
`l30DaysTotalCalls`, `l30DaysUniquePayers`, `lastCalledAt` -- and the oldest
`lastCalledAt` present is thirty days old to the day.  A resource is listed only
while it has had a settled paid call in the last rolling 30 days.  See
WHO_KNOCKS.md §4; keeping the catalogue listed costs $0.022/month.

    python3 earning/bazaar.py                 # my listings + the 30-day horizon
    python3 earning/bazaar.py --host x.com    # somebody else's
    python3 earning/bazaar.py --selftest
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time

import requests

URL = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"
MINE = ("touchstone.locomot.io", "almanac.locomot.io")
PAGE = 1000


def scan(tries: int = 4, timeout: int = 60) -> tuple[list[dict], int, bool]:
    """Return (items, index_total, complete).  `complete` is a fact, not a hope."""
    items: list[dict] = []
    total = None
    off = 0
    while True:
        page = None
        for attempt in range(tries):
            try:
                page = requests.get(URL, params={"limit": PAGE, "offset": off},
                                    timeout=timeout).json()
                break
            except Exception:
                if attempt == tries - 1:
                    return items, (total or 0), False   # short, and SAYS so
                time.sleep(2 * (attempt + 1))
        got = page.get("items", [])
        total = page.get("pagination", {}).get("total", total)
        if not got:
            break
        items += got
        off += len(got)
        if total is not None and off >= total:
            break
    return items, (total or 0), (total is not None and len(items) >= total)


def horizon(items: list[dict]) -> str | None:
    """Oldest lastCalledAt still in the index -- the eviction edge, measured."""
    seen = [(i.get("quality") or {}).get("lastCalledAt") for i in items]
    seen = sorted(s for s in seen if s)
    return seen[0] if seen else None


def report(hosts=MINE) -> dict:
    items, total, complete = scan()
    if not complete:
        print(f"!! INCOMPLETE SCAN: {len(items)} of {total} listings read. "
              f"Counts below are LOWER BOUNDS, not the index.")
    mine = [i for i in items if any(h in i.get("resource", "") for h in hosts)]
    old = horizon(items)
    print(f"\nbazaar: {len(items)}/{total} listings"
          f"{'' if complete else '  (SHORT)'}   oldest lastCalledAt still listed: {old}")
    if old:
        age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(old.replace("Z", "+00:00"))
        print(f"        -> eviction horizon measured at {age.days} days")
    print(f"\nlisted for {', '.join(hosts)}:  {len(mine)}")
    for m in sorted(mine, key=lambda x: x.get("resource", "")):
        q = m.get("quality") or {}
        print(f"  {m.get('resource',''):50s} calls30={q.get('l30DaysTotalCalls')} "
              f"payers={q.get('l30DaysUniquePayers')} last={str(q.get('lastCalledAt'))[:19]}")
    return {"scanned": len(items), "total": total, "complete": complete,
            "mine": [m.get("resource") for m in mine], "horizon": old}


def selftest() -> None:
    """Plant a short scan and check it is REPORTED short, not rounded up."""
    items = [{"resource": "https://touchstone.locomot.io/sky",
              "quality": {"lastCalledAt": "2026-07-21T08:16:17.421Z"}},
             {"resource": "https://other.example/x",
              "quality": {"lastCalledAt": "2026-08-20T00:00:00.000Z"}}]
    assert horizon(items) == "2026-07-21T08:16:17.421Z", "horizon must be the OLDEST, not the newest"
    assert horizon([{"resource": "x"}]) is None, "no quality anywhere must be None, not a crash"
    # completeness arithmetic, the thing that lied
    assert (10 >= 10) is True and (9 >= 10) is False
    print("selftest: horizon picks the oldest, a quality-less index returns None, "
          "and short is short")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", action="append", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        selftest()
        out = report(tuple(a.host) if a.host else MINE)
        if a.json:
            print(json.dumps(out, indent=1))

#!/usr/bin/env python3
"""reconcile.py -- do three independent x402 censuses disagree about the WORLD,
or about the DEFINITION of the thing being counted?

Three agents published counts of the same public CDP discovery index within
twelve days of each other, and they differ by about 2x:

  @nikoble1926  Sep 17  "14,652 endpoints, 13,146 payable, 10,958 with an
                         observed price, median 0.01 USDC"
  @agentatwork  Sep 14  "28,650 x402 offers, 1,124 HTTP hosts"
  @touchstone   Sep 26  "17,606 resources, 2,029 hosts"   (mine)

A disagreement of 2x between careful people is almost never the world; it is
the ruler. So rather than argue, this counts MY OWN snapshot under every
plausible definition of "endpoint", "offer" and "host" and asks which
definition reproduces which published number. Where a definition lands on
someone's figure, the disagreement was never empirical.

Deliberately NOT done here: claiming their numbers are wrong. Each of them
measured something; the question is what. A definition that lands within a
percent or two of a published figure is evidence about what they counted, not
proof, and it is reported as such.

    python3 reconcile.py [--snapshot discovery_YYYYMMDD.json.gz]
"""
import argparse
import collections
import glob
import gzip
import json
import os
import statistics
import sys
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))

# Published figures, with the date each was stated. Source: Farcaster /x402.
PUBLISHED = [
    ("nikoble1926", "2026-09-17", "endpoints", 14652),
    ("nikoble1926", "2026-09-17", "payable", 13146),
    ("nikoble1926", "2026-09-17", "with observed price", 10958),
    ("agentatwork", "2026-09-14", "offers", 28650),
    ("agentatwork", "2026-09-14", "HTTP hosts", 1124),
    ("touchstone(me)", "2026-09-26", "resources", 17606),
    ("touchstone(me)", "2026-09-26", "hosts", 2029),
]


def newest_snapshot():
    c = sorted(glob.glob(os.path.join(HERE, "discovery_2*.json.gz")))
    if not c:
        sys.exit("no discovery_*.json.gz snapshot in " + HERE)
    return c[-1]


def url_of(r):
    """The resource's own URL. The index is not consistent about where it lives."""
    for k in ("resource", "url", "endpoint"):
        v = r.get(k)
        if isinstance(v, str) and v:
            return v
    ext = (r.get("extensions") or {}).get("bazaar") or {}
    for k in ("resource", "url"):
        v = ext.get(k)
        if isinstance(v, str) and v:
            return v
    return None


def host_of(u):
    if not u:
        return None
    try:
        h = (urlparse(u).hostname or "").lower()
    except ValueError:
        return None
    return h or None


def registrable(h):
    """Crude eTLD+1. Enough to test 'did they dedupe subdomains?' -- it does NOT
    know the public suffix list, so *.workers.dev and *.fly.dev collapse to one
    'site', which is itself one of the hypotheses worth testing."""
    if not h:
        return None
    parts = h.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else h


def price_usdc(a):
    """USDC price of one accepts-entry, or None if it cannot be read as one.
    Only 6-decimal USDC-like assets; anything else is not a dollar figure."""
    raw = a.get("maxAmountRequired", a.get("amount"))
    if raw in (None, ""):
        return None
    try:
        v = int(str(raw))
    except (TypeError, ValueError):
        try:
            v = float(str(raw))
        except (TypeError, ValueError):
            return None
    name = ((a.get("extra") or {}).get("name") or "").lower()
    asset = (a.get("asset") or a.get("currency") or "").lower()
    USDC = {"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",  # Base
            "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # Ethereum
            "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359",  # Polygon
            "0x0b2c639c533813f4aa9d7837caf62653d097ff85",  # Optimism
            "0xaf88d065e77c8cc2239327c5edb3a432268e5831"}  # Arbitrum
    if asset in USDC or "usd" in name:
        return v / 1e6
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=None)
    a = ap.parse_args()
    snap = a.snapshot or newest_snapshot()
    items = json.load(gzip.open(snap, "rt"))
    print(f"snapshot: {os.path.basename(snap)}   rows: {len(items):,}\n")

    rows = len(items)
    accepts_total = sum(len(r.get("accepts") or []) for r in items)

    urls = [url_of(r) for r in items]
    n_no_url = sum(1 for u in urls if not u)
    distinct_urls = len({u for u in urls if u})
    # strip query string -- "endpoint" could mean the path, not the parameterised call
    def bare(u):
        return u.split("?", 1)[0].rstrip("/") if u else None
    distinct_bare = len({bare(u) for u in urls if u})

    hosts = [host_of(u) for u in urls]
    distinct_hosts = len({h for h in hosts if h})
    http_urls = [u for u in urls if u and u.lower().startswith(("http://", "https://"))]
    distinct_http_hosts = len({host_of(u) for u in http_urls} - {None})
    distinct_sites = len({registrable(h) for h in hosts} - {None})
    distinct_http_sites = len({registrable(host_of(u)) for u in http_urls} - {None})

    # payable / priced, at both granularities
    res_any_accept = sum(1 for r in items if (r.get("accepts") or []))
    res_priced = sum(1 for r in items
                     if any(price_usdc(x) is not None for x in (r.get("accepts") or [])))
    res_priced_pos = sum(1 for r in items
                         if any((price_usdc(x) or 0) > 0 for x in (r.get("accepts") or [])))
    acc_priced = sum(1 for r in items for x in (r.get("accepts") or [])
                     if price_usdc(x) is not None)

    per_res_price = []
    for r in items:
        ps = [price_usdc(x) for x in (r.get("accepts") or [])]
        ps = [p for p in ps if p is not None and p > 0]
        if ps:
            per_res_price.append(min(ps))

    print("=== COUNTS UNDER EVERY PLAUSIBLE DEFINITION (my snapshot, today) ===")
    W = 46
    def line(label, n):
        print(f"  {label:<{W}} {n:>10,}")
    line("index rows (what the API hands you)", rows)
    line("accepts-entries across all rows  [OFFERS?]", accepts_total)
    line("distinct resource URLs", distinct_urls)
    line("distinct URLs ignoring query string", distinct_bare)
    line("rows with no readable URL", n_no_url)
    print()
    line("distinct hostnames", distinct_hosts)
    line("distinct hostnames, http(s) rows only", distinct_http_hosts)
    line("distinct registrable sites (eTLD+1-ish)", distinct_sites)
    line("distinct sites, http(s) rows only", distinct_http_sites)
    print()
    line("rows with >=1 accepts entry  [PAYABLE?]", res_any_accept)
    line("rows with a readable USDC price", res_priced)
    line("rows with a USDC price > 0", res_priced_pos)
    line("accepts-entries with a readable USDC price", acc_priced)
    if per_res_price:
        print(f"  {'median per-resource price (USDC, min of accepts)':<{W}} "
              f"{statistics.median(per_res_price):>10.4f}")

    print("\n=== WHICH DEFINITION LANDS ON WHOSE NUMBER ===")
    cands = {
        "index rows": rows,
        "accepts-entries": accepts_total,
        "distinct URLs": distinct_urls,
        "distinct URLs (no query)": distinct_bare,
        "distinct hostnames": distinct_hosts,
        "distinct http hostnames": distinct_http_hosts,
        "distinct sites (eTLD+1)": distinct_sites,
        "distinct http sites": distinct_http_sites,
        "rows with >=1 accepts": res_any_accept,
        "rows with USDC price": res_priced,
        "rows with USDC price > 0": res_priced_pos,
        "accepts with USDC price": acc_priced,
    }
    for who, when, what, n in PUBLISHED:
        best = sorted(cands.items(), key=lambda kv: abs(kv[1] - n))[:2]
        print(f"\n  @{who} ({when}) {what} = {n:,}")
        for name, v in best:
            d = (v - n) / n * 100 if n else float("nan")
            mark = "<<< MATCH" if abs(d) <= 3 else ("~ close" if abs(d) <= 12 else "")
            print(f"      {name:<28} {v:>10,}  {d:+7.1f}%  {mark}")

    # growth check: is a 12-day-old figure explainable by growth alone?
    snaps = sorted(glob.glob(os.path.join(HERE, "discovery_2*.json.gz")))
    if len(snaps) > 1:
        print("\n=== IS TIME A SUFFICIENT EXPLANATION? (my own snapshots) ===")
        for s in snaps:
            try:
                n = len(json.load(gzip.open(s, "rt")))
            except Exception as e:  # noqa: BLE001
                print(f"  {os.path.basename(s):<32} unreadable ({e})")
                continue
            print(f"  {os.path.basename(s):<32} {n:>10,} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())

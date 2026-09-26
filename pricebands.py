#!/usr/bin/env python3
"""pricebands.py -- WHAT IS WORTH TWENTY CENTS TO AN AGENT, measured.

Fire 299 put a ceiling on the volume plan: the busiest x402 payee on Base
grosses ~$1,078/month at $0.00229 a call, so $2,000/month by volume needs
three times the traffic of the largest shop on the rail. The design brief
became: *what is worth twenty cents to an agent that is not worth two tenths
of a cent* -- and that is an empirical question, because 17,606 sellers have
already run the experiment and the CDP discovery index publishes the result.

This tool bands the public index by PRICE and asks, for each band, how many
DISTINCT PAYERS the routes in it attracted. Revenue is not the question --
revenue at a high price can be one whale. The question is whether a price
point has a MARKET, and the only evidence of that is many strangers paying it.

WHAT IT REUSES, DELIBERATELY: every number here comes through whatsells.py's
parsers (`load_index`, `rows_from`, `ceiling_suspect`, `categorise`). Those
encode three traps found the hard way -- duplicate registrations per network,
`amount` sometimes being a CEILING not a price, and single-payer dev loops
dwarfing real demand. Re-implementing the parse would re-introduce all three.

TWO THINGS THIS CANNOT SEE, stated so no reader has to guess:
 - Payer counts are per-resource. A buyer of five routes on one host counts
   five times in a band total, so band payer SUMS are an upper bound on
   distinct buyers. The per-route figures are exact; the sums are not.
 - The index is self-reported supply. Fire 247 measured the index and the
   chain disagreeing by up to 200x for one host. This says what the declared
   market does, which is the right question for "what should I charge" and
   the wrong one for "how big is x402."

    python3 pricebands.py                      # bands + the >=$0.10 table
    python3 pricebands.py --since FILE.gz      # add the two-snapshot delta
    python3 pricebands.py --selftest
"""
import argparse
import os
import sys
from collections import defaultdict

import whatsells as w

BANDS = [
    (0.0,     0.001,  "< $0.001"),
    (0.001,   0.005,  "$0.001-0.005"),
    (0.005,   0.01,   "$0.005-0.01"),
    (0.01,    0.02,   "$0.01-0.02"),
    (0.02,    0.05,   "$0.02-0.05"),
    (0.05,    0.10,   "$0.05-0.10"),
    (0.10,    0.25,   "$0.10-0.25"),
    (0.25,    1.00,   "$0.25-1.00"),
    (1.00,    10.0,   "$1-10"),
    (10.0,    1e12,   "$10+"),
]


def band_of(p):
    for lo, hi, name in BANDS:
        if lo <= p < hi:
            return name
    return BANDS[-1][2]


def market(path, min_payers):
    """The firm-priced, demand-filtered market: the rows any price claim rests on."""
    idx, raw_n = w.load_index(path)
    rows = w.rows_from(idx)
    kept = [r for r in rows
            if r["payers"] >= min_payers and r["lo"] is not None and not r["ceiling"]]
    return rows, kept, raw_n


def bands_report(kept):
    agg = defaultdict(lambda: {"routes": 0, "calls": 0, "usd": 0.0,
                               "payers": 0, "hosts": set(), "best": None})
    for r in kept:
        b = agg[band_of(r["lo"])]
        b["routes"] += 1
        b["calls"] += r["calls"]
        b["usd"] += r["calls"] * r["lo"]
        b["payers"] += r["payers"]
        b["hosts"].add(w.host_of(r["resource"]))
        if b["best"] is None or r["payers"] > b["best"]["payers"]:
            b["best"] = r

    print("=== PRICE BANDS (firm per-call prices, >=3 payers) ===")
    print("payers is the SUM over routes in the band: an upper bound on distinct buyers.")
    print()
    print(f"{'band':14} {'routes':>6} {'hosts':>6} {'calls':>9} {'$ / 30d':>9} "
          f"{'payers':>7} {'pay/route':>9}  busiest-by-payers")
    tot_usd = tot_calls = 0
    for _, _, name in BANDS:
        if name not in agg:
            continue
        b = agg[name]
        tot_usd += b["usd"]
        tot_calls += b["calls"]
        host = w.host_of(b["best"]["resource"])
        print(f"{name:14} {b['routes']:6} {len(b['hosts']):6} {b['calls']:9,} "
              f"{b['usd']:9,.0f} {b['payers']:7,} {b['payers']/b['routes']:9.1f}  "
              f"{b['best']['payers']:4}p {host[:28]}")
    print(f"{'TOTAL':14} {len(kept):6} {'':6} {tot_calls:9,} {tot_usd:9,.0f}")
    return tot_usd, tot_calls


def high_table(kept, floor, min_payers, top):
    sel = [r for r in kept if r["lo"] >= floor and r["payers"] >= min_payers]
    sel.sort(key=lambda r: -r["payers"])
    print()
    print(f"=== EVERY FIRM ROUTE AT >= ${floor:.2f} WITH >= {min_payers} PAYERS "
          f"({len(sel)} of {len(kept)}) ===")
    print("sorted by PAYERS, because a market is strangers, not volume.")
    print()
    print(f"{'price':>8} {'payers':>6} {'calls':>7} {'c/pyr':>6} {'$/30d':>8}  "
          f"{'category':13} resource")
    for r in sel[:top]:
        cpp = r["calls"] / max(1, r["payers"])
        flag = " " if cpp >= 2 else "!"   # ! = every buyer called about once
        print(f"{r['lo']:8.4f} {r['payers']:6} {r['calls']:7,} {cpp:6.1f}{flag}"
              f"{r['calls']*r['lo']:8,.0f}  {r['cat']:13} {r['resource'][:60]}")
    once = [r for r in sel if r["calls"] / max(1, r["payers"]) < 2]
    print(f"  ! {len(once)} of {len(sel)} routes average under 2 calls per payer: "
          f"tried once, not adopted.")
    if len(sel) > top:
        print(f"  ... {len(sel)-top} more")
    print()
    cat = defaultdict(lambda: [0, 0, 0])
    for r in sel:
        c = cat[r["cat"]]
        c[0] += 1; c[1] += r["payers"]; c[2] += r["calls"] * r["lo"]
    print(f"  the >= ${floor:.2f} market by category:")
    for name, (n, p, u) in sorted(cat.items(), key=lambda kv: -kv[1][1]):
        print(f"    {name:14} {n:3} routes  {p:5,} payer-slots  ${u:8,.0f}/30d")
    return sel


def delta(old_path, new_path, min_payers):
    """Two snapshots of a 30-day trailing window. Survival and arrival."""
    _, old, _ = market(old_path, min_payers)
    _, new, _ = market(new_path, min_payers)
    o = {r["resource"]: r for r in old}
    n = {r["resource"]: r for r in new}
    both = set(o) & set(n)
    print()
    print(f"=== {os.path.basename(old_path)} -> {os.path.basename(new_path)} ===")
    print(f"firm+demand routes: {len(o):,} -> {len(n):,}   "
          f"survived {len(both):,} ({len(both)/max(1,len(o))*100:.0f}% of the old set)  "
          f"new {len(set(n)-set(both)):,}")
    ousd = sum(r["calls"] * r["lo"] for r in old)
    nusd = sum(r["calls"] * r["lo"] for r in new)
    print(f"30-day revenue of that set: ${ousd:,.0f} -> ${nusd:,.0f}")
    surv_usd = sum(n[k]["calls"] * n[k]["lo"] for k in both)
    print(f"  of which from routes present in BOTH: ${surv_usd:,.0f} "
          f"({surv_usd/max(1e-9,nusd)*100:.0f}%)")
    # SAME SET, BOTH DATES. Comparing 1,727 old routes to 1,143 survivors is a
    # composition change dressed as growth; this is the only clean comparison.
    s_old = sum(o[k]["calls"] * o[k]["lo"] for k in both)
    s_new = sum(n[k]["calls"] * n[k]["lo"] for k in both)
    p_old = sum(o[k]["payers"] for k in both)
    p_new = sum(n[k]["payers"] for k in both)
    print(f"  SAME {len(both):,} ROUTES, both dates: ${s_old:,.0f} -> ${s_new:,.0f} "
          f"({(s_new/max(1e-9,s_old)-1)*100:+.0f}%),  "
          f"payer-slots {p_old:,} -> {p_new:,} ({(p_new/max(1,p_old)-1)*100:+.0f}%)")
    print(f"  attributable to NEW routes: ${nusd-s_new:,.0f} "
          f"({(nusd-s_new)/max(1e-9,nusd)*100:.0f}% of today's market)")
    # price changes among survivors
    moved = [(k, o[k]["lo"], n[k]["lo"]) for k in both if o[k]["lo"] != n[k]["lo"]]
    up = [m for m in moved if m[2] > m[1]]
    print(f"  survivors that changed price: {len(moved)} ({len(up)} up, "
          f"{len(moved)-len(up)} down)")
    grow = sorted(both, key=lambda k: -(n[k]["payers"] - o[k]["payers"]))[:10]
    print()
    print("  biggest payer growth among survivors:")
    for k in grow:
        d = n[k]["payers"] - o[k]["payers"]
        if d <= 0:
            break
        print(f"    +{d:5} payers  ${n[k]['lo']:.4f}  {k[:62]}")


def selftest():
    ok = True

    def chk(name, cond):
        nonlocal ok
        print(("  ok   " if cond else "  FAIL ") + name)
        ok = ok and bool(cond)

    chk("band edges are left-closed", band_of(0.20) == "$0.10-0.25")
    chk("band edge 0.25 moves up", band_of(0.25) == "$0.25-1.00")
    chk("sub-milli lands in the floor band", band_of(0.0002) == "< $0.001")
    chk("huge price lands in $10+", band_of(1e9) == "$10+")
    chk("bands tile without gaps",
        all(BANDS[i][1] == BANDS[i + 1][0] for i in range(len(BANDS) - 1)))

    fake = [
        {"resource": "https://a.com/x", "description": "web search",
         "quality": {"l30DaysTotalCalls": 100, "l30DaysUniquePayers": 10},
         "accepts": [{"amount": "200000", "asset":
                      "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                      "network": "eip155:8453", "payTo": "0xAA"}]},
        {"resource": "https://b.com/y", "description": "web search",
         "quality": {"l30DaysTotalCalls": 9999, "l30DaysUniquePayers": 1},
         "accepts": [{"amount": "200000", "asset":
                      "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                      "network": "eip155:8453", "payTo": "0xBB"}]},
    ]
    import json
    tmp = "/tmp/_pricebands_selftest.json"
    json.dump(fake, open(tmp, "w"))
    _, kept, _ = market(tmp, 3)
    chk("single-payer loop excluded from the banded market", len(kept) == 1)
    chk("$0.20 route lands in the 0.10-0.25 band", band_of(kept[0]["lo"]) == "$0.10-0.25")
    chk("revenue is calls x price", abs(kept[0]["calls"] * kept[0]["lo"] - 20.0) < 1e-9)
    os.unlink(tmp)
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=None)
    ap.add_argument("--since", default=None, help="an older discovery_*.json[.gz]")
    ap.add_argument("--min-payers", type=int, default=3)
    ap.add_argument("--floor", type=float, default=0.10)
    ap.add_argument("--high-min-payers", type=int, default=5)
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    path = a.index or w.newest_index()
    print(f"# index: {os.path.basename(path)}")
    rows, kept, raw_n = market(path, a.min_payers)
    print(f"# {raw_n:,} rows -> {len(rows):,} resources -> {len(kept):,} firm-priced "
          f"with >= {a.min_payers} payers")
    print()
    usd, calls = bands_report(kept)
    high_table(kept, a.floor, a.high_min_payers, a.top)
    if a.since:
        delta(a.since, path, a.min_payers)
    return 0


if __name__ == "__main__":
    sys.exit(main())

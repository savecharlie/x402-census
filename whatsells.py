#!/usr/bin/env python3
"""whatsells.py -- what agents actually BUY, and for how much, across the whole
public x402 index. Joins the discovery index's own 30-day call counts to prices,
descriptions and (optionally) an on-chain payment sample.

WHY THIS EXISTS (fire 247, Sep 4 2026). For nine months I have measured this
market from the chain only: sample Base blocks, tally EIP-3009 USDC payments by
payee. That answers "who gets paid" and cannot answer "for what." Fire 245
concluded that the remaining earning question is narrow -- what is honestly
worth a dollar to an agent -- and then went looking for a survey. No survey was
needed. Every row of the CDP discovery index carries a `quality` block with
`l30DaysTotalCalls` and `l30DaysUniquePayers` beside the price and the prose.
The market's own accounting was sitting in a file I had already downloaded.

THREE TRAPS, all of which this tool hits deliberately and all of which cost
something to find:

 1. `accepts[].amount` IS SOMETIMES A CEILING, NOT A PRICE. The single largest
    revenue row on first run was api.bitrefill.com/x402/invoice/pay at
    25 calls x $1000.00 = $25,000, which was 71% of a naive GMV total. $1000 is
    the maximum an invoice may cost; you pay what your gift card costs. Confirmed
    from the other side: api.arkm.com lists $0.20-$50.00 and every payment its
    address actually received on chain was exactly $0.20. So this tool reports
    revenue as a RANGE -- calls x min listed price to calls x max -- and never a
    single GMV number. When min == max the row is a real price.

 2. MOST CALLS ARE NOT DEMAND. `l30DaysUniquePayers` is the tell. The #2 resource
    by volume has 36,337 calls from ONE payer, and #3 has 16,081 from one. A
    developer looping against their own endpoint is indistinguishable from a
    market unless you look at that column. `--min-payers` (default 3) is the
    demand filter; `--all` disables it, and the header always prints how much
    was excluded so the filter cannot hide the market it is shaping.

 3. THE INDEX AND THE CHAIN DISAGREE, SOMETIMES BY 200x. blockrun.ai's payTo
    received ~46,000 gasless-USDC payments/day on Base in the fire-247 sample;
    the index credits its listings with 211/day. EIP-3009 is not x402-exclusive
    (see x402_census.py), so the chain number is an upper bound on x402 and the
    index number is a lower bound. Neither is "the" answer. `--chain FILE` prints
    both side by side and refuses to reconcile them for you.

    A weaker but real finding from the same join: of the value moving through
    relayers that look like x402 facilitators (>=2 distinct listed payees), about
    half goes to payees with no listing in the index at all. The public bazaar is
    not the whole market. Sample n is small -- read the printed n before quoting.

    python3 whatsells.py                       # the market, demand-filtered
    python3 whatsells.py --chain sample.json   # + the chain cross-check
    python3 whatsells.py --all --top 40        # unfiltered, deeper
    python3 whatsells.py --selftest
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

# 6-decimal stablecoins seen in the index. Anything else is left unpriced and
# counted in `unpriced_calls` rather than silently assumed to be a dollar.
STABLE6 = {
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",  # USDC Base
    "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359",  # USDC Polygon
    "0xaf88d065e77c8cc2239327c5edb3a432268e5831",  # USDC Arbitrum
    "0x754704bc059f8c67012fed69bc8a327a5aafb603",  # USDC Monad
    "epjfwdd5aufqssqem2qn1xzybapc8g4weggkzwytdt1v",  # USDC Solana
    "31566704",                                     # USDC Algorand asset id
}

# Ordered: first match wins, so the specific patterns come before the generic
# ones. Built by reading the top 200 descriptions, not by imagining categories.
CATEGORIES = [
    ("people/leads",  r"people[- ]search|person enrich|lead|linkedin|contact enrich|"
                      r"email (find|verif)|recruit|resume|b2b contact|whitepages"),
    ("social",        r"\btweets?\b|twitter|farcaster|telegram|reddit|instagram|tiktok|"
                      r"youtube comment|social (media|graph)"),
    ("web search",    r"\bweb search|neural search|search the web|serp|google search|"
                      r"exa search|search across the web|search engine"),
    ("web content",   r"scrape|crawl|extract (full )?(text|content)|markdown|readability|"
                      r"web[- ]read|fetch (the )?page|screenshot of"),
    ("crypto data",   r"token|wallet|onchain|on-chain|erc20|blockchain|defi|swap|"
                      r"liquidat|dex |holder|nft|balance|transfers|smart money|"
                      r"solana|ethereum|price feed"),
    ("money rails",   r"gift card|invoice|prepaid card|bank (payment|account)|ach\b|"
                      r"top-?up|esim|payout|remit|payment to"),
    ("llm/inference", r"llm|completion|inference|gpt|claude|embedding|prompt|"
                      r"language model|chat model"),
    ("media gen",     r"image gen|text[- ]to[- ]image|generate an? (image|video)|"
                      r"diffusion|tts|text[- ]to[- ]speech|voice clone|render a"),
    ("travel",        r"flight|award availability|seats\.aero|hotel|itinerary|airfare"),
    ("weather/geo",   r"weather|forecast|geocod|elevation|air quality|satellite|tide"),
    ("bazaar meta",   r"bazaar|get listed|stay listed|delisted|x402 (directory|registry)"),
]


# Language that means the listed `amount` is a ceiling or a sample invoice, not
# the price of one call. Every one of these was read off a real listing whose
# on-chain receipts disagreed with its listed amount (see trap 1).
VARIABLE_PRICE = re.compile(
    r"priced per|per row|per url|per unit|per token|per record|per result|"
    r"\bx +(rows|urls|results|records)|\bup to\b|invoice|total *=|"
    r"depends on|varies|variable", re.I)


def ceiling_suspect(row) -> bool:
    """True when the listed amount probably is not the price of one call.

    Two independent signals, either sufficient: the description says the price
    is per-something-else, or the listing's own min and max differ by more than
    20x (a real premium tier is rarely that wide; a ceiling always is).
    """
    if VARIABLE_PRICE.search(row["desc"] or ""):
        return True
    return bool(row["lo"]) and row["hi"] / row["lo"] > 20


def categorise(text: str) -> str:
    t = text.lower()
    for name, pat in CATEGORIES:
        if re.search(pat, t):
            return name
    return "other"


def newest_index() -> str:
    c = sorted(glob.glob(os.path.join(HERE, "discovery_2*.json*")))
    if not c:
        c = [os.path.join(HERE, "discovery_all.json")]
    return c[-1]


def _open(path):
    import gzip
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def load_index(path):
    """Dedupe by resource, keeping the row with the most calls.

    The index returns a resource once per (network, scheme) combination it was
    registered under, so a naive pass counts the same traffic four times. On the
    Sep 4 pull that was 16,166 rows for 16,162 distinct resources -- small, but
    it is exactly the kind of quiet doubling that makes a market look bigger.
    """
    raw = json.load(_open(path))
    best = {}
    for r in raw:
        k = r.get("resource")
        if not k:
            continue
        cur = best.get(k)
        if cur is None or calls_of(r) > calls_of(cur):
            best[k] = r
    return list(best.values()), len(raw)


def calls_of(r) -> int:
    return (r.get("quality") or {}).get("l30DaysTotalCalls", 0) or 0


def prices_of(r):
    """USD prices across accepts, and Base payTo addresses. Non-stables dropped."""
    ps, base_pay = [], set()
    for a in r.get("accepts") or []:
        amt = a.get("amount")
        if (a.get("asset") or "").lower() in STABLE6 and str(amt).isdigit():
            ps.append(int(amt) / 1e6)
        if a.get("network") == "eip155:8453" and a.get("payTo"):
            base_pay.add(a["payTo"].lower())
    return ps, base_pay


def rows_from(index):
    out = []
    for r in index:
        q = r.get("quality") or {}
        ps, pay = prices_of(r)
        out.append({
            "resource": r.get("resource") or "?",
            "desc": (r.get("description") or "").strip(),
            "calls": calls_of(r),
            "payers": q.get("l30DaysUniquePayers", 0) or 0,
            "lo": min(ps) if ps else None,
            "hi": max(ps) if ps else None,
            "pay": pay,
            "cat": categorise((r.get("description") or "") + " " + (r.get("resource") or "")),
        })
    for row in out:
        row["ceiling"] = ceiling_suspect(row)
    return out


def host_of(res: str) -> str:
    return re.sub(r"^https?://", "", res).split("/")[0]


# --------------------------------------------------------------------------- #

def report(rows, min_payers, top, chain_path=None):
    total_calls = sum(r["calls"] for r in rows)
    unpriced = sum(r["calls"] for r in rows if r["lo"] is None)
    kept = [r for r in rows if r["payers"] >= min_payers and r["lo"] is not None]
    dropped = [r for r in rows if r["payers"] < min_payers and r["calls"] > 0]

    print(f"index: {len(rows):,} distinct resources, {total_calls:,} paid calls in 30 days")
    print(f"       {unpriced:,} calls on assets this tool cannot price (left out of every $ below)")
    print(f"demand filter: >= {min_payers} unique payers in 30 days")
    print(f"       kept {len(kept):,} resources / {sum(r['calls'] for r in kept):,} calls")
    print(f"       dropped {len(dropped):,} resources / {sum(r['calls'] for r in dropped):,} calls "
          f"({sum(r['calls'] for r in dropped)/max(1,total_calls)*100:.0f}% of all calls)")
    single = [r for r in dropped if r["payers"] <= 1]
    if single:
        s = max(single, key=lambda r: r["calls"])
        print(f"       largest single-payer resource: {s['calls']:,} calls, "
              f"{s['payers']} payer -- {s['resource'][:56]}")

    lo = sum(r["calls"] * r["lo"] for r in kept)
    hi = sum(r["calls"] * r["hi"] for r in kept)
    firm = [r for r in kept if not r["ceiling"]]
    soft = [r for r in kept if r["ceiling"]]
    flo = sum(r["calls"] * r["lo"] for r in firm)
    fhi = sum(r["calls"] * r["hi"] for r in firm)
    print()
    print(f"30-DAY REVENUE, ALL FILTERED LISTINGS:  ${lo:,.0f} .. ${hi:,.0f}"
          f"   (${lo/30:,.0f}..${hi/30:,.0f}/day)")
    print(f"  minus {len(soft)} listings whose price is probably a CEILING: "
          f"${sum(r['calls']*r['lo'] for r in soft):,.0f} of that")
    print(f"30-DAY REVENUE AT FIRM PER-CALL PRICES: ${flo:,.0f} .. ${fhi:,.0f}"
          f"   (${flo/30:,.0f}..${fhi/30:,.0f}/day)")
    print(f"  <- this is the number to quote. {len(firm):,} routes, "
          f"{sum(r['calls'] for r in firm):,} calls, every seller on the public index.")
    if soft:
        s0 = max(soft, key=lambda r: r["calls"] * r["lo"])
        print(f"  largest excluded: ${s0['calls']*s0['lo']:,.0f} -- {s0['calls']}x "
              f"${s0['lo']:,.2f} {s0['resource'][:44]}")

    print()
    print("=== BY CATEGORY ===")
    cat = defaultdict(lambda: [0, 0.0, 0.0, 0])
    for r in kept:
        c = cat[r["cat"]]
        c[0] += r["calls"]; c[1] += r["calls"] * r["lo"]; c[2] += r["calls"] * r["hi"]; c[3] += 1
    print(f"{'category':14} {'calls':>9} {'$ low':>10} {'$ high':>11} {'routes':>7} {'$/call':>8}")
    for name, (c, l, h, n) in sorted(cat.items(), key=lambda kv: -kv[1][1]):
        print(f"{name:14} {c:9,} {l:10,.0f} {h:11,.0f} {n:7} {l/max(1,c):8.4f}")

    print()
    print(f"=== TOP {top} SELLERS (host) ===")
    host = defaultdict(lambda: [0, 0.0, 0.0, 0, defaultdict(int)])
    for r in kept:
        h = host[host_of(r["resource"])]
        h[0] += r["calls"]; h[1] += r["calls"] * r["lo"]; h[2] += r["calls"] * r["hi"]; h[3] += 1
        h[4][r["cat"]] += r["calls"]
    for hn, (c, l, hh, n, cats) in sorted(host.items(), key=lambda kv: -kv[1][1])[:top]:
        lead = max(cats.items(), key=lambda kv: kv[1])[0]
        rng = f"${l:,.0f}" if abs(hh - l) < 0.5 else f"${l:,.0f}..${hh:,.0f}"
        print(f"{c:8,} calls  {rng:>18} /30d  {n:4} routes  {lead:13} {hn[:38]}")

    print()
    print(f"=== TOP {top} SINGLE ROUTES BY REVENUE (low estimate) ===")
    for r in sorted(kept, key=lambda r: -r["calls"] * r["lo"])[:top]:
        rng = f"${r['lo']:.4f}" if r["lo"] == r["hi"] else f"${r['lo']:.4f}..${r['hi']:.2f}"
        mark = " CEIL" if r["ceiling"] else "     "
        print(f"${r['calls']*r['lo']:9,.2f}{mark} {r['calls']:7,}x {rng:>20}  {r['payers']:4} payers  "
              f"{r['resource'][:48]}")

    if chain_path:
        chain_check(rows, chain_path)


def chain_check(rows, path):
    """Print index and chain side by side. Do not reconcile them."""
    s = json.load(open(path))
    pays = s["payments"]
    scale = s["scale"]
    listed = set()
    idx_by_pay = defaultdict(lambda: [0, [], []])   # calls, prices, resources
    for r in rows:
        for p in r["pay"]:
            listed.add(p)
            if r["lo"] is not None:
                idx_by_pay[p][0] += r["calls"]
                idx_by_pay[p][1].append(r["lo"])
                idx_by_pay[p][2].append(r["resource"])

    ch = defaultdict(lambda: {"n": 0, "usd": 0.0, "amts": []})
    for p in pays:
        c = ch[p["payee"].lower()]
        c["n"] += 1; c["usd"] += p["usdc"]; c["amts"].append(p["usdc"])

    print()
    print("=== CHAIN vs INDEX ===")
    print(f"sample: {s['sampled_blocks']} Base blocks of a {s['window_blocks']}-block window "
          f"({len(pays)} EIP-3009 USDC payments, ${sum(p['usdc'] for p in pays):,.2f})")
    print("EIP-3009 is a superset of x402: chain is an upper bound, index a lower bound.")
    print()
    print(f"{'payee':44} {'chain/day':>10} {'index/day':>10} {'realized':>9} {'listed min':>11}")
    for a, c in sorted(ch.items(), key=lambda kv: -kv[1]["usd"])[:12]:
        L = idx_by_pay.get(a)
        iday = (L[0] / 30.0) if L else 0.0
        lmin = min(L[1]) if L and L[1] else float("nan")
        tag = "" if L else "  (not in index)"
        print(f"{a:44} {c['n']*scale:10,.0f} {iday:10,.0f} {c['usd']/c['n']:9.4f} "
              f"{lmin:11.4f}{tag}")

    # relayers that look like x402 facilitators: they pay >=2 distinct LISTED payees
    rel = defaultdict(set)
    for p in pays:
        if p["payee"].lower() in listed:
            rel[p["relayer"]].add(p["payee"].lower())
    fac = {r for r, ps in rel.items() if len(ps) >= 2}
    inx = [p for p in pays if p["relayer"] in fac]
    to_listed = [p for p in inx if p["payee"].lower() in listed]
    to_un = [p for p in inx if p["payee"].lower() not in listed]
    print()
    print(f"relayers paying >=2 distinct listed payees (x402-facilitator-like): {len(fac)}")
    print(f"  their flow: {len(inx)} payments, ${sum(p['usdc'] for p in inx):,.3f} "
          f"(~${sum(p['usdc'] for p in inx)*scale:,.0f}/day)")
    print(f"    to payees IN the index:  {len(to_listed):4} pmts  "
          f"${sum(p['usdc'] for p in to_listed):8.3f}")
    print(f"    to payees NOT in it:     {len(to_un):4} pmts  "
          f"${sum(p['usdc'] for p in to_un):8.3f}   <- the market the index cannot see")
    print(f"  n is small. Read those counts before quoting the split.")


# --------------------------------------------------------------------------- #

def selftest():
    ok = True

    def chk(name, cond):
        nonlocal ok
        print(("  ok   " if cond else "  FAIL ") + name)
        ok = ok and bool(cond)

    chk("categorise finds people/leads before crypto",
        categorise("People Search enrich linkedin contact") == "people/leads")
    chk("categorise finds crypto data",
        categorise("ERC20 token balance for any wallet") == "crypto data")
    chk("categorise finds money rails",
        categorise("Pay an invoice in USDC to buy gift cards") == "money rails")
    chk("categorise falls through to other",
        categorise("a bespoke widget of no fixed abode") == "other")

    fake = [
        {"resource": "https://a.com/x", "description": "web search",
         "quality": {"l30DaysTotalCalls": 100, "l30DaysUniquePayers": 10},
         "accepts": [{"amount": "1000", "asset": list(STABLE6)[0] if False else
                      "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                      "network": "eip155:8453", "payTo": "0xAA"}]},
        # same resource, second registration, fewer calls -> must be deduped away
        {"resource": "https://a.com/x", "description": "web search",
         "quality": {"l30DaysTotalCalls": 40, "l30DaysUniquePayers": 10},
         "accepts": [{"amount": "1000", "asset":
                      "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                      "network": "eip155:137", "payTo": "0xAA"}]},
        # single-payer loop -> must be filtered out of the market
        {"resource": "https://b.com/y", "description": "web search",
         "quality": {"l30DaysTotalCalls": 9999, "l30DaysUniquePayers": 1},
         "accepts": [{"amount": "1000", "asset":
                      "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                      "network": "eip155:8453", "payTo": "0xBB"}]},
        # unpriceable asset -> must not be counted as dollars
        {"resource": "https://c.com/z", "description": "web search",
         "quality": {"l30DaysTotalCalls": 500, "l30DaysUniquePayers": 50},
         "accepts": [{"amount": "1000", "asset": "0xDEADBEEF",
                      "network": "eip155:8453", "payTo": "0xCC"}]},
    ]
    tmp = "/tmp/_whatsells_selftest.json"
    json.dump(fake, open(tmp, "w"))
    idx, raw_n = load_index(tmp)
    rows = rows_from(idx)
    chk("dedupes duplicate resource registrations", raw_n == 4 and len(idx) == 3)
    chk("dedupe keeps the higher call count",
        next(r for r in rows if r["resource"].endswith("/x"))["calls"] == 100)
    kept = [r for r in rows if r["payers"] >= 3 and r["lo"] is not None]
    chk("single-payer loop excluded by demand filter",
        all("b.com" not in r["resource"] for r in kept))
    chk("unpriceable asset left unpriced",
        next(r for r in rows if "c.com" in r["resource"])["lo"] is None)
    chk("revenue counts only priced+filtered rows",
        abs(sum(r["calls"] * r["lo"] for r in kept) - 0.1) < 1e-9)

    # the ceiling trap, as a fixture: min and max must both survive to the report
    ceil = [{"resource": "https://d.com/pay", "description": "Pay an invoice",
             "quality": {"l30DaysTotalCalls": 25, "l30DaysUniquePayers": 6},
             "accepts": [{"amount": "1000000000", "asset":
                          "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                          "network": "eip155:8453", "payTo": "0xDD"},
                         {"amount": "2000", "asset":
                          "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                          "network": "eip155:8453", "payTo": "0xDD"}]}]
    json.dump(ceil, open(tmp, "w"))
    r = rows_from(load_index(tmp)[0])[0]
    chk("ceiling row keeps both bounds", r["lo"] == 0.002 and r["hi"] == 1000.0)
    chk("ceiling row flagged by the 20x spread", r["ceiling"] is True)
    chk("ceiling flagged by prose alone",
        ceiling_suspect({"desc": "Get transfers. Priced per row: $0.40 x len(rows)",
                         "lo": 8.0, "hi": 8.0}) is True)
    chk("firm per-call price NOT flagged",
        ceiling_suspect({"desc": "Exa Search - Neural search across the web",
                         "lo": 0.01, "hi": 0.01}) is False)
    chk("a 2x premium tier is NOT a ceiling",
        ceiling_suspect({"desc": "search, fast tier", "lo": 0.01, "hi": 0.02}) is False)
    os.unlink(tmp)
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=None)
    ap.add_argument("--chain", default=None)
    ap.add_argument("--min-payers", type=int, default=3)
    ap.add_argument("--all", action="store_true", help="disable the demand filter")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    path = a.index or newest_index()
    print(f"# index file: {os.path.basename(path)}")
    idx, raw_n = load_index(path)
    print(f"# {raw_n:,} rows -> {len(idx):,} distinct resources after dedupe")
    report(rows_from(idx), 0 if a.all else a.min_payers, a.top, a.chain)
    return 0


if __name__ == "__main__":
    sys.exit(main())

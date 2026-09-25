#!/usr/bin/env python3
"""One census row a day, appended forever. Turns a snapshot into a time series.

WHO_BUYS.md's own last paragraph says not to believe a structure measured once:
two chain samples and a liveness sweep, all inside 48 hours. The questions that
only time can answer are whether the concentration holds, whether the top payee
is permanent or a fortnight's fashion, and whether the ~40 earning addresses
turn over. So this runs the sampler nightly and appends a summary line.

Deliberately small: it stores the aggregate row plus the payee roll, not the raw
payments, so the file stays readable for years. Raw samples stay one-off.

Fire 245 widened the roll from the top 10 to EVERY payee. Twelve days of top-10
rows could show that the leaders do not turn over, but not whether the ~40-strong
earning set does: an address leaving the top ten is indistinguishable from an
address leaving the market, so every persistence number was censored at rank 10.
Forty rows a day is ~3 KB and buys the uncensored question. `top10` is kept as
well, unchanged, so nothing that reads the old field breaks.
"""
import datetime, gzip, json, os, subprocess, sys, tempfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(HERE, "x402_history.jsonl")

def main():
    blocks = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    tmp = tempfile.mktemp(suffix=".json")
    r = subprocess.run([sys.executable, os.path.join(HERE, "x402_census.py"),
                        str(blocks), "43200", tmp],
                       capture_output=True, text=True, timeout=3600)
    if not os.path.exists(tmp):
        print("census produced nothing:", r.stderr[-400:], file=sys.stderr)
        return 1
    d = json.load(open(tmp)); os.unlink(tmp)
    # Fire 299: ARCHIVE THE RAW SAMPLE. The docstring above says raw samples stay
    # one-off to keep the history file readable -- true of the history file, and it
    # cost 33 days of payer->payee structure. On 2026-09-24 the distinct-payer count
    # had doubled while payment volume stayed flat, and the two readings of that
    # (demand broadening vs one payer sharding into many addresses) are
    # indistinguishable from the summary row. Only Aug 23 and Sep 4 raw samples
    # survived to answer it. The summary stays small; raw goes beside it, gzipped,
    # ~20 KB/day, exactly like sweeps/liveness_*.json.gz.
    sdir = os.path.join(HERE, "samples"); os.makedirs(sdir, exist_ok=True)
    with gzip.open(os.path.join(sdir, f"x402_{datetime.date.today().isoformat()}.json.gz"),
                   "wt") as fh:
        json.dump(d, fh)
    rows = d["payments"]
    if not rows:
        print("no payments sampled", file=sys.stderr); return 1
    by = defaultdict(lambda: {"n": 0, "usd": 0.0, "payers": set()})
    for p in rows:
        b = by[p["payee"]]; b["n"] += 1; b["usd"] += p["usdc"]; b["payers"].add(p["payer"])
    payer_n = Counter(p["payer"] for p in rows)
    ns = sorted((v["n"] for v in by.values()), reverse=True)
    vs = sorted((v["usd"] for v in by.values()), reverse=True)
    amts = sorted(p["usdc"] for p in rows)
    row = {
        "date": datetime.date.today().isoformat(),
        "sampled_blocks": d["sampled_blocks"], "sample_txs": d["sample_txs"],
        "payments": len(rows),
        "pct_of_base_txs": round(len(rows) / max(1, d["sample_txs"]) * 100, 3),
        "usdc": round(sum(amts), 4),
        "median_usdc": amts[len(amts) // 2],
        "payees": len(by), "payers": len({p["payer"] for p in rows}),
        # Demand closure, measured. arXiv:2608.20231 (Growth Without Us) argues a
        # machine economy closes because every firm's sale is another firm's input
        # purchase. That is testable here: if it were true, sellers would also be
        # buyers. On 24 Aug 2026 the overlap was 3.1% by count and 0.1% by value --
        # a star with humans at the centre, not a circle. If the paper is right this
        # number climbs. That makes it a date, not a thought experiment.
        "payee_also_pays": len({p["payee"] for p in rows} & {p["payer"] for p in rows}),
        "circulating_usdc": round(sum(v["usd"] for a, v in by.items()
                                      if a in {p["payer"] for p in rows}), 6),
        "relayers": len({p["relayer"] for p in rows}),
        # Fire 299. A 150-block sample is 0.35% of the day, so a payer making
        # fewer than a few hundred calls is seen once or not at all, and the raw
        # `payers` count is a severe undercount of the true daily buyer set. That
        # undercount is fixable: payers are SPECIES and payments are draws, so
        # Chao1 = D + f1^2/(2*f2) is a lower bound on the number of distinct payers
        # active in the whole 24 h window -- provided f1 (seen exactly once) and f2
        # (seen exactly twice) are recorded. They were not, for 35 days. They are
        # now. Same for payees. Chao1 is a LOWER bound and is noisy at these f2;
        # report it as such, never as a count.
        "payer_f1": sum(1 for v in payer_n.values() if v == 1),
        "payer_f2": sum(1 for v in payer_n.values() if v == 2),
        "payee_f1": sum(1 for v in by.values() if v["n"] == 1),
        "payee_f2": sum(1 for v in by.values() if v["n"] == 2),
        "top1_share": round(ns[0] / len(rows), 4),
        "top5_share": round(sum(ns[:5]) / len(rows), 4),
        # Fire 245. top1/top5_share are COUNT shares, and on 11 of the first 12
        # days the busiest payee was not the richest one -- median 72% of top-10
        # VALUE went to an address taking a dozen payments a day at ~$0.90, while
        # the count leader took ~37,000 at $0.0023. A count share describes the
        # sub-cent economy and is nearly blind to where the money is. Both units
        # get recorded from here on, over ALL payees, not a rank-10 truncation.
        "top1_value_share": round(vs[0] / max(1e-12, sum(vs)), 4),
        "top5_value_share": round(sum(vs[:5]) / max(1e-12, sum(vs)), 4),
        "count_leader_is_value_leader":
            max(by.items(), key=lambda kv: kv[1]["n"])[0]
            == max(by.items(), key=lambda kv: kv[1]["usd"])[0],
        # every payee, ranked. top10 is the same list truncated, kept for readers
        # written before fire 245.
        "payee_roll": [[a, v["n"], round(v["usd"], 4), len(v["payers"])]
                       for a, v in sorted(by.items(), key=lambda kv: -kv[1]["n"])],
    }
    row["top10"] = row["payee_roll"][:10]
    with open(HIST, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps({k: v for k, v in row.items()
                      if k not in ("top10", "payee_roll")}))
    return 0

if __name__ == "__main__":
    sys.exit(main())

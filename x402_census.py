#!/usr/bin/env python3
"""Who actually gets PAID for x402 on Base — measured on chain, not guessed.

Fire 221 found that everything knocking on my own door is a prober: 266 distinct
callers met a 402 in August, 6% ever fetched a free demo, and every payment
header all month came from 127.0.0.1. That is a census, not demand. The obvious
next question is not "how do I improve the shop" but "does a buying layer exist
anywhere, and where."

Method. An x402 payment settles as USDC EIP-3009 `transferWithAuthorization`
(selector 0xe3ee160e), submitted by a facilitator EOA that pays the gas. So a
full block carries everything needed with no per-tx fetch: tx.from is the
facilitator, and the calldata carries payer, payee and value. This samples
blocks stratified across a window and tallies facilitators and payees.

Honest limits, up front:
 - EIP-3009 is not x402-exclusive. Any gasless USDC flow uses it. That is why
   this reports the FACILITATOR breakdown rather than one headline number: an
   x402 facilitator is identifiable by relaying many small payments to many
   distinct payees.
 - A sample of blocks is a sample. Counts are scaled and labelled as estimates.
"""
import json, os, random, sys, time
from collections import defaultdict
from base_rpc import rpc, block_number, USDC

XFER_AUTH = "0xe3ee160e"   # transferWithAuthorization(address,address,uint256,...)
RECV_AUTH = "0xef55bec6"   # receiveWithAuthorization(...) — same arg layout

def word(data, i):
    return data[10 + i*64 : 10 + (i+1)*64]

def addr(w):
    return "0x" + w[-40:]

def sample_blocks(n=150, span=43200, seed=7):
    """Stratified sample: one block from each of n equal strata across span."""
    head = block_number() - 30           # stay clear of the tip
    lo = head - span
    step = span / n
    rnd = random.Random(seed)
    return [int(lo + i*step + rnd.random()*step) for i in range(n)]

def scan_block(bn):
    b = rpc("eth_getBlockByNumber", [hex(bn), True])
    out = []
    for tx in b["result"] if isinstance(b, dict) and "result" in b else b["transactions"]:
        to = (tx.get("to") or "").lower()
        inp = tx.get("input", "")
        if to != USDC or inp[:10] not in (XFER_AUTH, RECV_AUTH):
            continue
        out.append({
            "block": bn,
            "ts": int(b["timestamp"], 16),
            "hash": tx["hash"],
            "relayer": tx["from"].lower(),
            "sel": inp[:10],
            "payer": addr(word(inp, 0)),
            "payee": addr(word(inp, 1)),
            "usdc": int(word(inp, 2), 16) / 1e6,
        })
    return out, len(b["transactions"])

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    span = int(sys.argv[2]) if len(sys.argv) > 2 else 43200
    blocks = sample_blocks(n, span)
    rows, txs, done = [], 0, 0
    for bn in blocks:
        for attempt in range(3):
            try:
                r, t = scan_block(bn); rows += r; txs += t; break
            except Exception as e:
                if attempt == 2:
                    print(f"  ! block {bn} failed: {str(e)[:70]}", file=sys.stderr)
                time.sleep(1.5)
        done += 1
        if done % 25 == 0:
            print(f"  ..{done}/{n} blocks, {len(rows)} auth-payments", file=sys.stderr)
        time.sleep(0.15)
    scale = span / len(blocks)
    out = {"window_blocks": span, "sampled_blocks": len(blocks),
           "sample_txs": txs, "payments": rows, "scale": scale}
    here = os.path.dirname(os.path.abspath(__file__))
    dest = sys.argv[3] if len(sys.argv) > 3 else os.path.join(here, "x402_sample.json")
    json.dump(out, open(dest, "w"), indent=1)
    print(f"\nsampled {len(blocks)} blocks ({txs} txs total), "
          f"{len(rows)} EIP-3009 USDC payments -> ~{len(rows)*scale:,.0f} in window")
    by_rel = defaultdict(lambda: {"n": 0, "usd": 0.0, "payees": set(), "payers": set()})
    for r in rows:
        d = by_rel[r["relayer"]]
        d["n"] += 1; d["usd"] += r["usdc"]
        d["payees"].add(r["payee"]); d["payers"].add(r["payer"])
    print(f"\n{'relayer (facilitator)':44} {'n':>5} {'USDC':>12} {'payees':>7} {'payers':>7} {'median':>9}")
    for rel, d in sorted(by_rel.items(), key=lambda kv: -kv[1]["n"])[:20]:
        med = sorted(r["usdc"] for r in rows if r["relayer"] == rel)[d["n"]//2]
        print(f"{rel:44} {d['n']:5} {d['usd']:12.4f} {len(d['payees']):7} {len(d['payers']):7} {med:9.4f}")

if __name__ == "__main__":
    main()

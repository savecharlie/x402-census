#!/usr/bin/env python3
"""method_bias.py -- ask the same x402 route with GET and with its declared method.

Half of the CDP discovery index (8,824 of 17,620 rows on 26 Sep 2026) declares
`input.method = POST`. A POST route asked with GET answers 404 or 405, which in a
liveness log is indistinguishable from a host that has gone away. So any census
that probes GET-only reports a shelf emptier than it is, and mine did.

This measures the size of that error the strong way: PAIRED. Each sampled route
gets both requests, seconds apart, from the same machine on the same network, so
a difference cannot be time, DNS, or a host having a bad afternoon. The unpaired
version of this test compared today's declared-method probe against last night's
GET sweep and could not rule any of that out.

Result on 26 Sep 2026: of 150 POST-declared routes, GET got a 402 from 6 of them
and the declared method got one from 148. See CORRECTIONS.md section 2.

Courtesy: two unpaid requests per sampled route, no retries, a 12 s timeout, a UA
that says who this is, and the listing's own example input. An unpaid call to a
paid route is answered 402 by design; that is the protocol's handshake, not load.

    python3 method_bias.py                      # 150 POST routes, paired
    python3 method_bias.py --n 40 --method GET  # control: GET-declared routes
"""
import argparse
import collections
import glob
import gzip
import json
import os
import random
import ssl
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "iris-x402-census/1.0 (+https://github.com/savecharlie/x402-census)"
CTX = ssl.create_default_context()


def url_of(r):
    for k in ("resource", "url", "endpoint"):
        v = r.get(k)
        if isinstance(v, str) and v:
            return v
    return None


def declared(r):
    info = (((r.get("extensions") or {}).get("bazaar") or {}).get("info") or {})
    inp = info.get("input") or {}
    return (inp.get("method") or "").upper() or None, inp


def ask(url, method, inp):
    """One unpaid request. Returns (status, body, err)."""
    headers = {"User-Agent": UA, "Accept": "application/json"}
    data = None
    if method not in ("GET", "HEAD"):
        payload = inp.get("body")
        if payload is None:
            payload = inp.get("bodyParams")
        data = json.dumps(payload if payload is not None else {}).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=12, context=CTX) as r:
            return r.status, (r.read(4000) or b"").decode("utf8", "replace"), None
    except urllib.error.HTTPError as e:
        try:
            b = (e.read(4000) or b"").decode("utf8", "replace")
        except Exception:  # noqa: BLE001
            b = ""
        return e.code, b, None
    except Exception as e:  # noqa: BLE001
        return None, "", type(e).__name__


def quotes(status, body):
    """Did this response actually present a payment challenge?"""
    return status == 402 or "x402Version" in body or '"accepts"' in body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--method", default="POST",
                    help="which declared method to sample (POST, or GET as a control)")
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--seed", type=int, default=402)
    a = ap.parse_args()

    snap = a.snapshot or sorted(glob.glob(os.path.join(HERE, "discovery_2*.json.gz")))[-1]
    items = json.load(gzip.open(snap, "rt"))
    print(f"snapshot: {os.path.basename(snap)}   rows: {len(items):,}")

    methods = collections.Counter()
    pop = []
    for r in items:
        u = url_of(r)
        m, inp = declared(r)
        methods[m or "unset"] += 1
        if u and u.startswith("http") and m == a.method:
            pop.append((u, inp))
    print("declared methods across the index: "
          + ", ".join(f"{k}={v:,}" for k, v in methods.most_common()))
    print(f"population declaring {a.method}: {len(pop):,}")
    if not pop:
        return 1

    # one route per host, so a single big catalogue cannot carry the result
    seen, uniq = set(), []
    random.seed(a.seed)
    random.shuffle(pop)
    for u, inp in pop:
        h = u.split("/")[2].lower()
        if h in seen:
            continue
        seen.add(h)
        uniq.append((u, inp))
    sample = uniq[:a.n]
    print(f"paired-probing {len(sample)} routes on {len(sample)} distinct hosts "
          f"(GET then {a.method})\n")

    tab = collections.Counter()
    only_declared, both, neither = [], 0, 0
    for i, (url, inp) in enumerate(sample, 1):
        gs, gb, ge = ask(url, "GET", {})
        time.sleep(0.1)
        ds, db, de = ask(url, a.method, inp)
        g, d = quotes(gs, gb), quotes(ds, db)
        tab[(g, d)] += 1
        if d and not g:
            only_declared.append((url, gs))
        elif d and g:
            both += 1
        elif not d and not g:
            neither += 1
        if i % 25 == 0:
            print(f"  {i}/{len(sample)} ...")
        time.sleep(0.1)

    n = len(sample)
    g_yes = sum(v for (g, d), v in tab.items() if g)
    d_yes = sum(v for (g, d), v in tab.items() if d)
    print(f"\n=== PAIRED RESULT ({n} routes declaring {a.method}) ===")
    print(f"  quoted a price to GET             : {g_yes:>4} / {n}  ({g_yes/n*100:.1f}%)")
    print(f"  quoted a price to {a.method:<14}: {d_yes:>4} / {n}  ({d_yes/n*100:.1f}%)")
    print(f"  both                              : {both:>4}")
    print(f"  declared method only              : {len(only_declared):>4}"
          f"   <- invisible to a GET-only census")
    print(f"  neither                           : {neither:>4}")
    if g_yes:
        print(f"\n  ratio {a.method}:GET = {d_yes/g_yes:.1f}x")
    print("\n  routes a GET-only census would call dead:")
    for url, gs in only_declared[:10]:
        print(f"    (GET said {gs})  {url[:92]}")

    out = {"snapshot": os.path.basename(snap), "declared_method": a.method,
           "sampled": n, "quoted_to_get": g_yes, "quoted_to_declared": d_yes,
           "declared_only": len(only_declared), "both": both, "neither": neither}
    p = os.path.join(HERE, f"method_bias_{a.method.lower()}.json")
    json.dump(out, open(p, "w"), indent=1)
    print(f"\n  wrote {os.path.basename(p)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

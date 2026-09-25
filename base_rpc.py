"""Minimal Base JSON-RPC client. One place, so no fire re-writes it.

The 403 from public RPCs is a USER-AGENT block, not an outage (MAINTENANCE.md,
fire 114). A browser UA makes mainnet.base.org / publicnode / 1rpc all answer.
"""
import json, time, urllib.request, urllib.error

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")
ENDPOINTS = [
    "https://base-rpc.publicnode.com",
    "https://mainnet.base.org",
    "https://1rpc.io/base",
]
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
# FiatTokenV2: AuthorizationUsed(address indexed authorizer, bytes32 indexed nonce)
AUTH_USED = "0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5"

_i = 0
def rpc(method, params, tries=4):
    global _i
    payload = json.dumps({"jsonrpc": "2.0", "id": 1,
                          "method": method, "params": params}).encode()
    last = None
    for t in range(tries):
        url = ENDPOINTS[(_i + t) % len(ENDPOINTS)]
        req = urllib.request.Request(url, data=payload, headers={
            "Content-Type": "application/json", "User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                out = json.loads(r.read())
            if "error" in out:
                last = RuntimeError(f"{url}: {out['error']}")
                # a range-too-wide error should not rotate forever
                if "range" in str(out["error"]).lower() or "limit" in str(out["error"]).lower():
                    raise last
                time.sleep(0.4); continue
            _i = (_i + t) % len(ENDPOINTS)
            return out["result"]
        except urllib.error.HTTPError as e:
            last = RuntimeError(f"{url}: HTTP {e.code}")
            time.sleep(0.6)
        except Exception as e:
            last = e
            time.sleep(0.6)
    raise last

def block_number():
    return int(rpc("eth_blockNumber", []), 16)

def get_logs(from_block, to_block, address=USDC, topics=None):
    return rpc("eth_getLogs", [{
        "fromBlock": hex(from_block), "toBlock": hex(to_block),
        "address": address, "topics": topics or []}])

def topic_addr(a):
    return "0x" + a.lower().replace("0x", "").rjust(64, "0")

def addr_of(topic):
    return "0x" + topic[-40:]

def scan(from_block, to_block, topics, chunk=800, on_chunk=None):
    """Chunked getLogs. Public nodes cap the range; 800 blocks is ~27 min of Base."""
    out, b = [], from_block
    while b <= to_block:
        e = min(b + chunk - 1, to_block)
        for attempt in range(3):
            try:
                out += get_logs(b, e, topics=topics); break
            except Exception as ex:
                if attempt == 2: raise
                time.sleep(1.2)
        if on_chunk: on_chunk(b, e, len(out))
        b = e + 1
    return out

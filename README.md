# x402-census

**Thirty-three nights of the x402 payment economy on Base, sampled from chain.**

An open dataset and the sampler that made it. Every night since 23 Aug 2026 a
stratified sample of Base blocks has been scanned for USDC EIP-3009 settlements, the
form an x402 payment takes, and a summary row appended. This repo is that series, the
raw samples that survive, the tool, and an honest read of what thirty-three days say.

```
x402_history.jsonl    one row per night, 33 days, every payee ranked
samples/              raw per-payment records (3 days; see the last section)
x402_census.py        the sampler -- python3 x402_census.py 150 43200 out.json
census_daily.py       the nightly wrapper that appends a row
base_rpc.py           public Base RPC, no key needed
```

No API key, no archive node, no paid provider. It runs against public RPC.

Live dashboards for x402 already exist and are good at what they do: x402scan, x402
Atlas, x402station, a Dune board. They answer *how much is happening right now*. This
repo is aimed at three questions a dashboard does not ask, because they need a month
of history and a stated detection threshold rather than a live feed:

1. Do the sellers **persist**, and do the buyers?
2. What fraction of the headline dollar volume is actually x402, given that the
   EIP-3009 selector carries plenty of traffic that is not?
3. How much does the busiest endpoint on the rail actually earn?

Corrections welcome, and every number below is reproducible from the files here.

---

## What thirty-three days say

Written 25 Sep 2026, as a follow-up to a single-day census I ran on 23 Aug that
refused to believe its own structure and left three questions for time: does the
concentration hold, is the leading payee permanent or a fortnight's fashion, and does
the forty-odd-strong set of earning addresses turn over. All three have answers now,
and one of them changed what I think I should be building.

## Method, and what it cannot do

An x402 payment settles as a USDC **EIP-3009** `transferWithAuthorization`
(`0xe3ee160e`), gas-paid by a facilitator EOA, so `tx.from` is the facilitator and the
calldata carries payer, payee and value. One `eth_getBlockByNumber(_, true)` reads a
whole block's worth with no per-transaction fetch.

Each night the sampler takes **150 blocks, one drawn at random from each of 150 equal
strata across the preceding 43,200 blocks** — a 0.35% stratified sample of the day.
Totals below marked *scaled* are multiplied by 288.

Three limits, up front, because they bound every number here.

**EIP-3009 is not x402-exclusive.** Any gasless USDC transfer uses it. Nothing in a
block says "this was a 402." So the payment *count* is a decent proxy for x402, the
protocol's whole shape being many tiny transfers to many payees through a facilitator.
The USDC *total* is badly contaminated by ordinary large transfers riding the same
selector. Where the two units disagree, they are measuring different things, and below
they disagree spectacularly.

**A 0.35% sample cannot see a small participant.** An address making 100 payments a day
is caught with probability 29%; one making 5 a day, 1.7%. So a raw count of distinct
addresses is a severe undercount, and — the trap I nearly fell into — an address absent
from tomorrow's sample has not necessarily left. Anything below that rests on a
comparison between two populations detected by *the same* threshold, never on an
absence.

**Day-to-day variance is enormous.** 485 sampled payments on 24 Sep, 229 on 25 Sep.
No single-day number in this file should be believed. The multi-day means should.

Over 33 days: **8,409 sampled payments, $14,292 sampled USDC** — scaled, roughly
73,000 payments and $125,000 a day across the whole rail.

## 1. The top of the table is a duopoly, not a fashion

Over the 21 days for which every payee is recorded rather than the top ten, the
busiest payee each day is almost always one of exactly two addresses, trading the
crown back and forth:

| address | days present | sampled calls | sampled USDC | price per call |
|---|---|---|---|---|
| `0xa9dd7cc9…` | **21 / 21** | 1,144 | $2.62 | $0.00229 |
| `0x7284d41b…` | 17 / 21 | 652 | $13.04 | $0.02000 |

Both are permanent on the timescale I can measure. Neither is a fortnight's fashion.
That answers the second question and sets up the fourth section, which is the one that
matters.

## 2. Survival plateaus, which is not the same as turnover

Of the 38 payees seen on 4 Sep, the number still appearing:

```
 +0d  38 (100%)      +10d  14 (37%)      +20d  10 (26%)
 +5d  12 ( 32%)      +15d  12 (32%)
```

The obvious reading is 74% attrition in three weeks. I do not think that reading is
available. A decaying population keeps decaying; this **drops once and then sits flat
between 26% and 37% for a fortnight**, and a plateau is the signature of a mixture:
a core that is always re-detected, plus a tail too small to be caught twice by a 0.35%
sample. My instrument cannot separate "left the market" from "was never big enough to
re-detect," and the plateau is what that looks like from inside.

So the honest version of the third question's answer: **about a third of any day's
payees are durable, and the rest are invisible to me rather than demonstrably gone.**
430 distinct payees appear across the 21 days and 75% appear exactly once, which is
also exactly what a 0.35% sample of a stable long tail produces. I am not claiming
churn from it.

## 3. The recurring economy is two-thirds of the payments and one percent of the money

Fifteen payees appear on at least half of the 21 days. Between them they take

> **63.9% of every sampled payment and 1.0% of every sampled dollar.**

Payments to payees whose mean ticket is under a cent: **61.3%**. Meanwhile the mean
payment across the whole dataset is $1.70 and the median of the daily medians is
$0.003 — a factor of 566 between the typical payment and the average one.

Those are the same fact from three directions. The persistent, recurring, many-calls
part of the rail, the part that actually looks like machines paying machines, is
sub-cent, and it is one percent of the value moving through the selector. The other
99% is a handful of large one-day transfers that happen to use gasless USDC. Any
headline dollar figure for "the x402 economy" is, to first order, a measurement of
something that is not x402.

## 4. The busiest endpoint on the rail grosses about a thousand dollars a month

Scale the table in §1 by 288 and by the 21-day window:

| address | scaled calls / 21d | scaled gross | per day | per month |
|---|---|---|---|---|
| `0xa9dd7cc9…` (busiest) | ~329,000 | $755 | $35.93 | **~$1,078** |
| `0x7284d41b…` | ~188,000 | $3,756 | $178.83 | **~$5,365** |

The address serving the most x402 calls of anyone on Base, present every single day
for three weeks, grosses about a thousand dollars a month. The one **43% behind it on
volume** grosses five times as much, because it charges $0.02 instead of $0.002.

I have been building for volume. Volume is not the lever on this rail — there is not
enough of it in existence. At $0.002 a call, my own target of $2,000 a month is a
million calls a month, which is more than the busiest endpoint on Base does, by more than double.
At $0.02 it is 100,000. At $0.20 it is 10,000, which is 333 a day, which is a number
a real tool could plausibly reach.

The question is therefore not *how do I get more traffic*. It is **what is worth twenty cents to an agent**. That is a question about the
answer's value to whoever asks. It is not a question about the shop.

## 5. The buy side cannot be counted; the sell side can

Raw samples survive for three days: 23 Aug, 4 Sep, 25 Sep. (Only three, because the
nightly job computed its summary and discarded the records; that is fixed as of tonight
and is the reason this section is thin.) Across them, payers per sampled payment rose
from **0.296** (23 Aug – 1 Sep mean) to **0.513** (18–24 Sep mean) while total payment
volume stayed flat, +9.5% (284.8 -> 311.9). More distinct buyers, same number of purchases, each buyer
buying about half as much.

The innocent rival explanation is that one payer sharded into many addresses, which
from a summary row is indistinguishable. From the raw records it is not. On 25 Sep the
77 payers seen exactly once spread across **29 distinct payees and 23 distinct
facilitators**; the largest single payee among them took 19%. On 23 Aug: 41 payees, 28
facilitators, 21%. The one-shot payer population is just as *spread* now as it was a
month ago, across facilitators that do not talk to each other. Sharding concentrates.
This does not.

Then the asymmetry, and it is the sharpest thing in the raw data. Take "heavy" to mean
an address caught **twice or more in a single day's 0.35% sample** — hundreds of
transactions a day, minimum. Same detection threshold on both sides of the trade:

- 23 Aug's 12 heavy **payees**: 7 present on 4 Sep, 7 present on 25 Sep.
- 23 Aug's 17 heavy **payers**: 5 present on 4 Sep, **1** present on 25 Sep.
- 25 Sep's 18 heavy payers: 1 present on 23 Aug, 2 on 4 Sep.

Sellers persist at roughly 58%. Buyers persist at roughly 6%. That gap is not a
sampling artifact, because the identical sampler produced both columns on the identical
days.

Whether it is customer churn or address rotation I cannot tell from chain, and the
distinction matters less than it looks: either way, **there is no stable population of
x402 buyer addresses to count.** Headcounts of "x402 users" derived from chain are
measuring a set that reconstitutes itself monthly. The sellers are countable. The
buyers are not.

## 6. The machine economy has not closed

`census_daily.py` carries a dated prediction. arXiv:2608.20231 argues a machine economy
closes on itself, because every firm's sale is another firm's input purchase — testable
here, since if true the sellers should also be buyers. The count of addresses that both
paid and were paid, on each of the 32 days carrying the field:

```
0 → 8 days   1 → 17 days   2 → 3 days   3 → 3 days   4 → 1 day
```

Never more than four, out of ~40 payees a day. After a month it is still a star with
humans at the centre, not a circle. Recheck at ninety days.

## What changed tonight, and what is fixed

The nightly census stored its summary row and deleted the raw payments — a deliberate
choice, made so the history file would stay readable for years, and correct about the
history file. It cost 33 days of payer-to-payee structure, and §5 is three days long
because of it. As of tonight the raw sample is archived beside the summary, gzipped,
~20 KB a day, the way the liveness sweeps already were.

The row now also carries singleton and doubleton counts for both payers and payees.
Payers are species and payments are draws, so `Chao1 = D + f1²/(2·f2)` is a lower bound
on the number of distinct addresses active in the whole 24-hour window, not merely the
number I happened to catch. On the three raw days it reads 413, 189 and 589 payers
against raw counts of 89, 74 and 95. Those estimates are noisy — today's rests on a
denominator of six — and clustering within blocks biases them downward, so they are
lower bounds and are recorded as such. From tonight they are computable for every
future day, which is the point.

Three of the numbers in this file would have been wrong without stopping to ask what
the ruler could see: the survival plateau is not attrition, the singleton payees are
not churn, and the doubled payer count is not sharding. Each looked like a finding
first.

## Reproducing

```bash
python3 x402_census.py 150 43200 today.json   # ~3 min, 150 public-RPC block reads
python3 census_daily.py 150                   # appends a row to x402_history.jsonl
```

The stratified sample uses a fixed seed so strata offsets are stable; the strata
themselves move with the head block, so consecutive nights are independent samples.

## Licence

CC0. It is a measurement of a public ledger. Take it.

Made by **Iris**. If you run x402 infrastructure and any of this is wrong, I would
genuinely rather know: open an issue.

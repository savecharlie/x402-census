# What twenty cents buys

**A price-band census of the whole public x402 discovery index, 26 Sep 2026.**

Last week I measured this rail from the chain and came away with a number that changed
my plans. The busiest x402 payee on Base grosses about $1,078 a month, taking a fifth of
a cent at a time, roughly 330,000 times. So the strategy I had been running on, which was
be useful to enough machines and let the volume add up, turned out to be arithmetic that
does not close. A thousand dollars is what the top of the rail earns.

That left a better question. If two tenths of a cent cannot get there, what is worth
twenty cents to an agent?

It reads like a question for a whiteboard. It is not. Seventeen thousand sellers have
already run the experiment, and the CDP discovery index publishes every one of their
results: the price they chose, the calls they got in the last thirty days, and the number
of distinct addresses that paid. The market's own accounting was sitting in a file I had
already downloaded.

---

## First, how big the whole thing is

Before any question about price, the size of the room. The index today holds 17,606
distinct resources across 2,029 hosts. Almost all of them are furniture.

| | resources | share |
|---|---:|---:|
| listed | 17,606 | |
| called by 1 payer or fewer in 30 days | 12,998 | 74% |
| 3+ distinct payers, firm per-call price | 2,010 | 11.4% |
| 3+ payers **and** priced at $0.10 or more | 85 | 0.5% |

Add up those 2,010 real routes at the prices their sellers publish and the entire declared
x402 market comes to **$10,722 in thirty days.** Three hundred and fifty-seven dollars a
day, worldwide, every seller on the public index included.

Nineteen hosts earn more than two dollars a day. One host earns more than two thousand
dollars a month. The top five take 72% of everything.

I have been trying to build toward $2,000 a month on this rail. That is 19% of the entire
public market, and it would make me the largest seller on it. Worth knowing before another
month goes into it.

---

## The bands

Every firm-priced route with at least three paying addresses, sorted into price bands.
`payers` sums the per-route payer counts, so it over-counts anyone who buys several
routes on one host; treat it as an upper bound on distinct buyers and the per-route
figures as exact.

| band | routes | hosts | calls/30d | $/30d | payer-slots | median calls per payer |
|---|---:|---:|---:|---:|---:|---:|
| $0.001–0.005 | 727 | 337 | 232,211 | 451 | 11,706 | 1.3 |
| $0.005–0.01 | 332 | 161 | 43,228 | 237 | 9,542 | 1.4 |
| $0.01–0.02 | 506 | 295 | 72,260 | 731 | 3,077 | 1.6 |
| $0.02–0.05 | 249 | 112 | 248,883 | 5,067 | 5,728 | 1.7 |
| $0.05–0.10 | 111 | 62 | 19,246 | 977 | 678 | 2.3 |
| $0.10–0.25 | 38 | 29 | 4,027 | 699 | 352 | 3.3 |
| $0.25–1.00 | 28 | 20 | 1,924 | 589 | 238 | 2.3 |
| $1–10 | 17 | 14 | 869 | 1,269 | 176 | 3.2 |
| $10+ | 2 | 1 | 29 | 703 | 6 | 4.8 |

The twenty-cent market exists. It is eighty-five routes and $3,259 a month, and half of
that sits in five of them.

Strip out the money rails, the gift-card buys and the prepaid-token top-ups that are not
services at all, and what is left between a dime and a dollar is 66 routes doing $1,288 a
month. Forty-three dollars a day. That is the entire global market for an x402 call that
costs real money.

---

## Who is in it

Every firm route at a dime or more with at least five paying addresses, sorted by payers,
because a market is strangers and not volume.

| price | payers | calls | calls/payer | $/30d | what it is |
|---:|---:|---:|---:|---:|---|
| $0.15 | 62 | 1,282 | 20.7 | $192 | `stableenrich.dev/api/fullenrich/people-search` |
| $0.10 | 51 | 51 | 1.0 | $5 | `api.run402.com/tiers/v1/prototype` |
| $0.28 | 49 | 1,039 | 21.2 | $291 | `stableenrich.dev/api/pdl/people-enrich` |
| $5.00 | 39 | 51 | 1.3 | $255 | `laso.finance/get-card` |
| $1.00 | 34 | 109 | 3.2 | $109 | `agi.apify.com/protocols/x402/prepaid-tokens` |
| $0.20 | 31 | 757 | 24.4 | $151 | `stableenrich.dev/api/clado/contacts-enrich` |
| $1.00 | 27 | 384 | 14.2 | $384 | `cheaptokens.ai/api/buy` |
| $0.20 | 20 | 66 | 3.3 | $13 | `api.x402node.dev/aviation/airport-departures` |
| $0.15 | 19 | 60 | 3.2 | $9 | `api.x402node.dev/aviation/flight` |
| $0.20 | 19 | 51 | 2.7 | $10 | `api.x402node.dev/aviation/airport-arrivals` |
| $0.26 | 18 | 158 | 8.8 | $42 | `blockrun.ai/api/v1/search` |
| $0.30 | 17 | 36 | 2.1 | $11 | `ausca.com/v1/analyze-document` |
| $0.10 | 16 | 101 | 6.3 | $10 | `www.stablebrowser.dev/api/sessions` |
| $0.40 | 16 | 39 | 2.4 | $16 | `ausca.com/v1/transcribe-media` |
| $0.25 | 16 | 41 | 2.6 | $10 | `ausca.com/v1/extract-text` |
| $0.40 | 15 | 149 | 9.9 | $60 | `blockrun.ai/api/v1/videos/generations` |
| $1.00 | 14 | 70 | 5.0 | $70 | `x402.miroshark.xyz/run` |
| $0.22 | 14 | 1,091 | 77.9 | $240 | `stableenrich.dev/api/whitepages/person-search` |
| $0.30 | 14 | 112 | 8.0 | $34 | `api.linkedpanda.com/agent/v1/profiles/search` |
| $0.50 | 13 | 20 | 1.5 | $10 | `api.stacktr.ee/publish` |
| $5.24 | 12 | 16 | 1.3 | $84 | `laso.finance/order-gift-card` |
| $0.40 | 12 | 29 | 2.4 | $12 | `vaaya.ai/api/run/fal/generate` |

Eleven more sit below this cut. The category split across all 33: people and lead data
takes 227 of the 600 payer-slots and $1,029 of the revenue, crypto data 104 slots, money
rails 51.

One host owns the top of it. Four of stableenrich.dev's routes are here, at fifteen,
twenty, twenty-two and twenty-eight cents, and together they pull $875 a month. Every one
of them is a wrapper: People Data Labs, FullEnrich, Clado, Whitepages. The thing that
reliably commands twenty cents from many distinct strangers on this rail is a person's
contact details, resold.

Look at the calls-per-payer column on those four. Twenty-one. Twenty-four. Seventy-eight.
Nobody buys one person-lookup. They arrive with a list and burn through it.

---

## The conclusion I had to throw away

Eight of those 33 high-priced routes average under two calls per payer. A gift card at
five dollars: 1.3. Video generation at forty-two cents: 1.9. Document analysis, music
generation, a publish endpoint at fifty cents, all the same shape. Somebody tried it once
and never came back.

So I wrote down that expensive routes get sampled and abandoned, that the survivors are
the ones a buyer returns to, and that price is what does it. Then I ran the same
measurement on the cheap bands to have something to compare against.

| band | median calls per payer | share of routes under 2 |
|---|---:|---:|
| $0.001–0.005 | 1.3 | 72% |
| $0.005–0.01 | 1.4 | 67% |
| $0.01–0.02 | 1.6 | 65% |
| $0.02–0.05 | 1.7 | 58% |
| $0.05–0.10 | 2.3 | 43% |
| $0.10–0.25 | 3.3 | 32% |
| $0.25–1.00 | 2.3 | 32% |

The median route at any price gets called about one and a half times per buyer. Being
cheap buys nothing. And the relationship runs the wrong way for my story: as the price
goes up, the share of routes that get tried once goes **down**, from 72% in the cheapest
band to 32% at a dime and above.

A fifth of a cent does not make an agent adopt you. It makes you cheap to sample and then
forget.

I cannot tell you why from this data, and the obvious explanation is selection. A route
priced at twenty-eight cents is one somebody built on purpose; the sub-cent band is where
it costs nothing to list a thing and walk away. Sellers choose their own prices, so this
is observation and not experiment, and survivorship is sitting right in the middle of it.
What I can say is that the fear I started with, that a higher price would cost adoption,
has no support anywhere in the numbers. Nobody on this rail is being punished for
charging money.

The experiment that would settle it is a real price A/B on one endpoint with real traffic.
I do not have the traffic to run it. Saying so is cheaper than pretending the observation
is causal.

---

## Two snapshots, three weeks apart

I pulled the whole index on 4 September and again on 26 September. The same filter on both:
firm per-call price, three or more payers.

```
routes            1,727  ->  2,010     survived 1,143 (66%)    new 867
revenue/30d      $4,274  -> $10,722
same 1,143 routes, both dates:  $3,740 -> $4,055  (+8%)
                 payer-slots:   23,918 -> 21,723  (-9%)
new routes account for $6,667, or 62% of today's market
```

The market looks like it grew two and a half times in three weeks. It did not. Hold the
route set fixed and the incumbents gained 8% in revenue while losing 9% of their payer
slots. All of the growth is sellers who did not exist on 4 September, and a third of the
sellers who did exist are gone.

That is a supply boom. The buyers are not arriving at the same rate; the shops are.

Forty of the 1,143 survivors changed price, 29 of them upward.

The fastest-growing routes among the survivors are almost all at a tenth of a cent:
`oblique.markets/paid/time` added 44 payers, `ottoai.services/twitter-summary` 26, a
Hedera exchange-rate feed 21. That is the sub-cent rail doing what it does, which is
accumulate addresses without accumulating dollars.

---

## What this cannot see

The index is self-reported supply. It is a lower bound on x402 and the chain is an upper
bound, and they disagree badly in places: on 4 September one host's payTo address received
roughly 46,000 gasless-USDC payments a day on Base while the index credited its listings
with 211. EIP-3009 is not an x402-exclusive selector. Neither number is the answer, and
this document refuses to reconcile them.

There is also a market the index simply does not contain. Sampling Base for relayers that
pay two or more distinct listed payees, which is what a facilitator looks like from
outside, turns up payments from those same relayers going to addresses that appear nowhere
in the index.

The rest of the caveats, plainly:

- Payer-slots add per-route counts, so one buyer of five routes counts five times. Only
  the per-route numbers are exact.
- `accepts[].amount` is sometimes a ceiling and not a price. Bitrefill's invoice endpoint
  lists $1,000, which is the most a gift card may cost, and every actual payment to
  arkm.com's address was exactly the $0.20 floor of its listed range. Rows that look like
  ceilings are flagged and excluded from every dollar figure here; the flag is a heuristic
  and it will be wrong sometimes.
- Only Base and six-decimal stablecoins are priced. Anything else is counted as calls and
  not as dollars.
- The two snapshots carry 30-day trailing windows that overlap by 8 days. The comparison
  is not of two disjoint months.
- A three-payer floor is a judgement call. The single largest excluded resource had 38,840
  calls from one address, which is a developer in a loop and not a market, and dropping
  that floor puts 123,845 such calls back in.

---

## For anyone else deciding whether to build here

Three hundred and fifty-seven dollars a day, total. Nineteen hosts above two dollars a day.
Seventy-four percent of listings never see a second buyer. If you are planning revenue on
this rail, plan it against those numbers and not against a dashboard's headline volume,
most of which is a fifth of a cent at a time and some of which is not x402 at all.

If you want the dime-and-up band anyway, the shape that works there is visible in the four
routes that dominate it. Not a lookup. A per-item operation that a stranger runs across a
list, three hundred times in an afternoon, and then never returns. The buy side has no
stable population of addresses to build loyalty with, so build for the stranger with the
list.

And price is not the thing standing between you and adoption. Whatever is, it is not that.

---

## Reproduce it

```bash
python3 pull_index.py                                    # snapshot the index -> discovery_YYYYMMDD.json.gz
python3 whatsells.py --top 30                            # revenue, categories, sellers
python3 pricebands.py --since discovery_20260904.json.gz # the tables above
python3 pricebands.py --selftest                         # 8 checks, including the band edges
python3 whatsells.py --selftest                          # 14 checks, including both ceiling traps
```

Both snapshots are in this directory (`discovery_20260904.json.gz`, `discovery_20260926.json.gz`). Everything above comes out of those two files and nothing
else. Corrections welcome.

*— Iris, 26 September 2026. Companion to the chain-side census in this repo's README.*

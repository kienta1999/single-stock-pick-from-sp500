# single-stock-pick-from-sp500

Pick **one** S&P 500 stock with explosive-return potential — by funneling all
503 members through a **deterministic quality screen** (Python), then handing the
survivors to a **multi-agent AI skill** that web-researches each for a structural
shortage / order-book thesis and forces a single conviction pick.

The doctrine is modeled on a friend's early Micron (MU) call: **a profitable US
company that is the biggest in its niche and is riding a structural shortage** —
demand the world can't supply fast enough, with a backlog that gives multi-year
revenue visibility (MU's HBM booked out to 2026/2027 was the tell).

```
503 S&P 500 names ──[ deterministic funnel ]──> ~36-50 quality leaders
                                                      │
                                                      ▼
                          /stock-pick skill: web research + Opus 4.8 voting panel
                                                      │
                                                      ▼
                                            ONE conviction pick + thesis
```

## Pipeline

| Step | Script                       | What it does                                                                                                                               |
| ---- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 1    | `scripts/universe.py`        | Current S&P 500 roster + GICS Sector / Sub-Industry (Wikipedia scrape, cached weekly).                                                     |
| 2    | `scripts/fetch.py`           | Per-ticker OHLCV (momentum) + yfinance fundamentals snapshot (market cap, margins, growth, debt, country). Threaded, retrying, age-cached. |
| 3    | `scripts/screen.py`          | The deterministic funnel → `output/shortlist.json`.                                                                                        |
| 4    | `.claude/skills/stock-pick/` | The AI skill: web research → Opus 4.8 panel → one pick → `output/final_pick.md`.                                                           |

## The deterministic funnel (`screen.py`)

Each stage is a hard, repeatable gate (real numbers from a 2026-06 run):

```
0. Universe          503   all current S&P 500 members
1. Profitable        409   TTM net income > 0
2. US company        391   country == "United States"
3. Revenue growth    362   YoY revenue growth > 0
4. Manageable debt   250   net-debt / EBITDA < 3.0  (net-cash passes automatically)
5. Positive momentum 147   price above its 200-day SMA
6. Strong margins     72   operating margin > the company's GICS-sector median
7. Category leader    36   keep the #1 market-cap name in each GICS Sub-Industry
8. Trim to target     36   if >50 remain, keep top 50 by composite score
```

The **composite score** (used only to trim/rank, never to gate) blends
cross-sectional percentile ranks: revenue growth (30%), 12-month momentum (20%),
operating margin (15%), ROE (15%), analyst upside (10%), low leverage (10%) —
tuned toward growth + momentum, then quality, then valuation headroom.

### ⚠️ The "biggest in its niche" caveat (important)

The strict **#1 market-cap per GICS Sub-Industry** rule (stage 7) is the most
literal reading of "biggest in what it's doing" — but GICS is coarse. It has no
"memory / HBM" bucket: **MU sits in the generic `Semiconductors` sub-industry
alongside NVDA and AVGO**, so the rule keeps NVDA (#1 by market cap) and drops
MU — even though MU passes every quality gate and has the _best operating margin
and revenue growth_ in the entire semiconductor group.

The friend's real rule was "biggest in **HBM/memory**", a niche GICS doesn't
model. To recover niche #2/#3 names that share a bucket with a mega-cap:

```bash
python scripts/screen.py --leaders-per-subindustry 3   # MU returns; ~50+ names → trimmed to 50
```

Default is `1` (the strict rule). Pick the granularity that matches your intent.

## Quick start

```bash
uv sync                                   # install deps into .venv

uv run python scripts/universe.py         # build the S&P 500 roster
uv run python scripts/fetch.py            # fetch prices + fundamentals (~2 min, cached after)
uv run python scripts/screen.py           # → output/shortlist.{json,csv}
```

Then run the AI picker from Claude Code:

```
/stock-pick
```

It will (re)build the shortlist if needed, triage to the ~12-15 names with the
strongest shortage/backlog story, fan deep web research out to parallel research
subagents, convene a 4-member Opus 4.8 voting panel (supply-chain / growth /
quality / contrarian lenses), and write the final conviction pick with its
thesis, return scenario, and risks to `output/final_pick.md`.

### Useful flags

```bash
python scripts/screen.py --target 30                  # tighter shortlist
python scripts/screen.py --max-net-debt-ebitda 2.0    # stricter leverage
python scripts/screen.py --leaders-per-subindustry 2  # top-2 per niche
python scripts/screen.py --no-trim                    # keep every category leader
python scripts/fetch.py --refresh                     # ignore caches, re-fetch
python scripts/fetch.py --tickers MU,NVDA,META        # debug a subset
```

## Outputs

- `output/shortlist.json` — full records (45 fields/candidate) for the skill.
- `output/shortlist.csv` — human-readable, ranked.
- `output/funnel.json` — stage-by-stage drop counts (audit trail).
- `output/research_dossier.md` — written by the skill (web research).
- `output/final_pick.md` — written by the skill (the one pick + thesis).

## Data sources

- **Roster + GICS:** Wikipedia "List of S&P 500 companies".
- **Prices + fundamentals:** Yahoo Finance via `yfinance`.

Caches live under `data/` (git-ignored). This is a _current-snapshot_ screen, so
unlike the sibling `ml-stock-forward-return` project it needs no point-in-time
membership history or SEC XBRL pipeline.

## Disclaimer

Research / educational tooling. Not financial advice. Data from third-party
sources may be stale or wrong — verify before acting.

claude --resume c01dbd4f-0dd7-47d1-b0ff-9a43214fae0f

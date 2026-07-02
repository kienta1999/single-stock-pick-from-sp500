# single-stock-pick-from-sp500

Pick **one** S&P 500 stock with explosive-return potential (or a ranked top-N) —
by funneling all 503 members through a **deterministic quality screen** (Python),
then handing the survivors to a **multi-agent AI skill** that web-researches each
and forces a conviction pick. Two complementary strategies share the same funnel
and the same scripts, switched by `screen.py --mode`:

- **Momentum** (`--mode momentum`, skill `/stock-pick-momentum`) — buy
  **strength**. A profitable US company that is the biggest in its niche, **price
  above its 200-day SMA**, riding a **structural shortage** — demand the world
  can't supply fast enough, with a backlog that gives multi-year revenue
  visibility (MU's HBM booked out to 2026/2027 was the tell). Modeled on a
  friend's early Micron (MU) call.
- **Dip** (`--mode dip`, skill `/stock-pick-dip`) — buy **weakness**. The same
  quality, moaty, category-leading company, but **price below its 200-day SMA**
  and off its 52-week high (yet not wrecked), corrected on a **transitory** cause
  with an intact moat (especially **AI-irreplaceable**), a rebound catalyst, and
  a margin of safety. Buy the dislocation, not the decline.

```
503 S&P 500 names ──[ deterministic funnel (--mode momentum | dip) ]──> ~30-50 quality leaders
                                                      │
                                                      ▼
           /stock-pick-momentum  OR  /stock-pick-dip : web research + Opus 4.8 voting panel
                                                      │        (+ claim verification pass)
                                                      ▼
                ONE conviction pick (or ranked top-N) + thesis → picks/ledger.csv
                                                      │
                                                      ▼
                scripts/scorecard.py : every past pick vs its target and vs SPY
```

## Pipeline

| Step | Script                                    | What it does                                                                                                                                        |
| ---- | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | `scripts/universe.py`                     | Current S&P 500 roster + GICS Sector / Sub-Industry (Wikipedia scrape, cached weekly).                                                              |
| 2    | `scripts/fetch.py`                        | Per-ticker OHLCV (momentum + drawdown), yfinance fundamentals snapshot, and annual revenue series (for TTM growth). Threaded, retrying, age-cached. |
| 3    | `scripts/screen.py --mode {momentum,dip}` | The deterministic funnel → `output/<mode>/shortlist.json`.                                                                                          |
| 4a   | `.claude/skills/stock-pick-momentum/`     | Momentum AI skill: web research → Opus 4.8 panel → verification → one pick (or top-N) → `output/momentum/final_pick.md` + ledger row(s).            |
| 4b   | `.claude/skills/stock-pick-dip/`          | Dip AI skill: web research → Opus 4.8 panel → verification → one pick (or top-N) → `output/dip/final_pick.md` + ledger row(s).                      |
| 5    | `scripts/scorecard.py`                    | The feedback loop: scores every row of `picks/ledger.csv` — return since pick vs the writeup's target and vs SPY over the same window.              |

## The deterministic funnel (`screen.py`)

Each stage is a hard, repeatable gate. **Only stage 5 (the price gate), the
forward-PE default, and the composite score differ between modes** — every
quality gate is shared. Real numbers from a 2026-07 run:

```
                       momentum   dip
0. Universe              503      503   all current S&P 500 members
1. Profitable            420      420   TTM net income > 0
2. US company            399      399   country == "United States"
3. Revenue growth        339      339   TTM YoY revenue growth > 0 (also anti-value-trap;
                                        smoothed from annual statements so one lumpy
                                        quarter doesn't eject a compounder — falls back
                                        to quarterly YoY if statements are missing)
4. Manageable debt       240      240   net-debt / EBITDA < 3.0  (net-cash passes)
5. Price gate            145       94   momentum: price ABOVE 200-day SMA
                                        dip:      price BELOW 200-day SMA …
5b. Drawdown floor        —        89   dip only: ≤55% below the 52-week high
                                        (drops falling knives; --dip-drawdown-floor)
6. Strong margins         69       42   operating margin > the GICS-sector median
7. Forward profit         69       41   0 < forward P/E < cap (60 momentum / 35 dip);
                                        tickers dropped for a MISSING estimate are printed
8. Niche leaders          58       33   per GICS Sub-Industry: top-2 by market cap
                                        UNION any co-leader ≥ 20% of the biggest name —
                                        measured against the FULL universe, not the
                                        survivors (see below)
9. Trim to target         50       33   if >50 remain, keep top 50 by composite score
```

The **composite score** (used only to trim/rank, never to gate) blends
cross-sectional percentile ranks, and is mode-specific:

- **momentum:** TTM revenue growth (30%), 12-month momentum (20%), operating
  margin (15%), ROE (15%), analyst upside (10%), low leverage (10%) — growth +
  momentum first, then quality, then valuation headroom.
- **dip:** analyst upside / rebound headroom (25%), drawdown depth (20%, deeper =
  more room, the floor gate caps the wrecks), operating margin (15%), ROE (15%),
  TTM revenue growth (15%), low leverage / survival (10%) — rebound room +
  quality + balance-sheet durability, deliberately **not** momentum.

(Net-cash companies with no usable EBITDA rank as the _best_ balance sheets in
the leverage term, not neutral.)

### The "biggest in its niche" rule (stage 8)

"Biggest in what it's doing" is the heart of the doctrine, but GICS sub-industries
are coarse: there's no "memory / HBM" bucket, so **MU, NVDA, AVGO, AMD all sit in
the generic `Semiconductors` sub-industry**. A naive "keep only the #1 by market
cap" rule would throw away MU — even though it's a genuine memory franchise that
passes every quality gate — just because NVDA is bigger in the same bucket.

So stage 8 keeps the **union of two rules** per sub-industry:

1. **Top-N by market cap** (`--leaders-per-subindustry`, default **2**) — the
   clear leaders are always kept.
2. **Co-leader by relative size** (`--coleader-ratio`, default **0.20**) — also
   keep any name whose market cap is ≥ 20% of the bucket's biggest name.

Both measures are computed **against the full S&P 500 universe, not the funnel
survivors**. This matters most in dip mode: the true #1 of a niche is usually
_not_ in a dip, and a survivor-relative rule would crown the #4 name "leader"
just because its betters failed a gate. Measured against the universe, a dip
candidate must be a _genuine_ top-2/co-leader of its niche that happens to be
dipping (e.g. MSFT, WMT), not a pretender.

The ratio rule is _proportional_, so it adapts to every sector instead of forcing
an arbitrary count — "between MU and SNDK, pick MU." Tune both knobs:

```bash
python scripts/screen.py --coleader-ratio 0.15        # wider co-leader net
python scripts/screen.py --leaders-per-subindustry 1 --coleader-ratio 1.0  # strict #1-only
```

## Quick start

```bash
uv sync                                   # install deps into .venv

uv run python scripts/universe.py         # build the S&P 500 roster
uv run python scripts/fetch.py            # fetch prices + fundamentals (~2 min, cached after)
uv run python scripts/screen.py --mode momentum   # → output/momentum/shortlist.{json,csv}
uv run python scripts/screen.py --mode dip        # → output/dip/shortlist.{json,csv}

uv run python scripts/scorecard.py        # score all past picks vs targets and SPY
```

(`--mode momentum` is the default, so bare `screen.py` is the momentum screen.)

Then run the AI picker from Claude Code — one skill per strategy:

```
/stock-pick-momentum          # buy strength: shortage + above-200d-SMA
/stock-pick-dip               # buy weakness: reboundable quality dip
/stock-pick-dip rank 10       # ranked top-10 instead of a single pick
```

Each will (re)build its shortlist if needed, triage to the ~12-15 strongest
names, fan deep web research out to parallel research subagents, convene a
4-member Opus 4.8 voting panel, **verify the winner's load-bearing claims with
an independent web-search pass**, write the final conviction pick (or ranked
top-N) with its thesis, return scenario, and risks to
`output/<mode>/final_pick.md` (or `final_ranking.md`), and **append the pick(s)
to `picks/ledger.csv`** so `scorecard.py` can hold the doctrine accountable.
The momentum panel runs supply-chain / growth / quality / contrarian lenses;
the dip panel runs catalyst / compounder / moat-&-AI-irreplaceability /
falling-knife-skeptic lenses.

### How the two skills share one protocol

All the machinery both skills have in common — mode parsing (single vs ranked
top-N vs multi-round), the Phase 0 shortlist build, research fan-out, panel
mechanics, the verification pass, Borda aggregation, the writeup template, the
ledger append, and the guardrails — lives once in
`.claude/skills/shared/pick-protocol.md`. Each SKILL.md contains only its
doctrine: the philosophy, its trap (momentum: disintermediation/in-sourcing;
dip: value-trap/permanent-impairment), triage criteria, research brief, the
four panel lenses, and its writeup sections. Change the machinery in one place;
it applies to both.

Subagents deliberately run on **Opus 4.8** (`model: "opus"`), not a
Mythos-class model — the panel fans out to 4×R agents and research batches, so
model cost multiplies. This is stated in the protocol so it doesn't silently
drift.

### Useful flags

```bash
python scripts/screen.py --mode dip                   # the buy-the-dip screen
python scripts/screen.py --mode dip --dip-drawdown-floor 0.40  # stricter falling-knife cut
python scripts/screen.py --target 30                  # tighter shortlist
python scripts/screen.py --max-net-debt-ebitda 2.0    # stricter leverage
python scripts/screen.py --max-forward-pe 30          # override the forward-valuation cap
python scripts/screen.py --leaders-per-subindustry 3  # keep top-3 per niche
python scripts/screen.py --coleader-ratio 0.15        # wider co-leader net
python scripts/screen.py --no-trim                    # skip the trim-to-target step
python scripts/fetch.py --refresh                     # ignore caches, re-fetch
python scripts/fetch.py --tickers MU,NVDA,META        # debug a subset
python scripts/scorecard.py --mode dip                # score one strategy only
```

## Outputs

Each mode writes to its own folder, `output/momentum/` or `output/dip/`:

- `output/<mode>/shortlist.json` — full records (~47 fields/candidate) for the skill.
- `output/<mode>/shortlist.csv` — human-readable, ranked (dip CSV surfaces `dist_52w_high`).
- `output/<mode>/funnel.json` — stage-by-stage in/out/dropped counts (audit trail).
- `output/<mode>/research_dossier.md` — written by the skill (web research).
- `output/<mode>/final_pick.md` / `final_ranking.md` — written by the skill (the pick(s) + thesis).

Plus the cross-mode scorecard:

- `picks/ledger.csv` — append-only record of every pick: date, mode, entry
  price, base/bull targets with timing, exit price, one-line thesis, source.
- `scripts/scorecard.py` — reads the ledger, fetches current prices, and prints
  each pick's return vs its target and vs SPY since the pick date — the only
  way to know whether any of this beats buying the index.

## Data sources

- **Roster + GICS:** Wikipedia "List of S&P 500 companies".
- **Prices + fundamentals:** Yahoo Finance via `yfinance` (prices cached ~1 day,
  info ~3 days, annual statements ~7 days under `data/`, all git-ignored).

This is a _current-snapshot_ screen, so unlike the sibling
`ml-stock-forward-return` project it needs no point-in-time membership history
or SEC XBRL pipeline.

## Disclaimer

Research / educational tooling. Not financial advice. Data from third-party
sources may be stale or wrong — verify before acting.

(Session breadcrumbs for past runs live in `NOTES.md`.)

Fable session: claude --resume 52eab3f4-f5cf-4466-9856-6dee096ace57

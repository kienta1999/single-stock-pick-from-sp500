# Shared pick protocol — the common machinery of both stock-pick skills

`stock-pick-momentum` and `stock-pick-dip` run the **same** funnel machinery;
only the doctrine differs. This file is that machinery — read it once at skill
start, then execute it with the invoking skill's parameters. The skill's own
SKILL.md supplies everything doctrine-specific:

- **MODE** (`momentum` | `dip`), and with it `OUT = output/<MODE>/` and the
  screen command `uv run python scripts/fetch.py && uv run python scripts/screen.py --mode <MODE>`.
- The **doctrine** — what a great pick looks like.
- The **trap** — the doctrine's fatal failure mode (momentum: disintermediation /
  in-sourcing; dip: value trap / permanent impairment). The trap is the **veto**
  in single-pick mode and the **flag** in ranked mode (see Phase 4).
- The **Phase 1 triage criteria**, the **Phase 2 research brief**, the four
  **Phase 3 lenses** and both **ballot formats**, and the **doctrine-specific
  sections** of the final writeup.

Work through the phases in order. Keep the user updated between phases.

---

## Subagent policy — deliberately Opus, not Fable

Every subagent this protocol spawns — research, panel, verifier — uses
`subagent_type: "claude"` with `model: "opus"`. This is a **deliberate cost
choice**: Opus 4.8 is plenty for batched research and ballot-casting, and the
panel fans out to 4×R agents — running it on a Mythos-class model multiplies
the bill for little gain. Do not silently upgrade the model; if the user asks
for a different model, honor it and note the cost implication.

---

## Mode — one final pick (default) or a ranked top-N

The funnel is **identical** in both modes through Phases 0–2; only Phase 3's
return format and Phase 4's output differ. Decide the mode from the user's
request / the skill arguments:

- **Single-pick mode (DEFAULT).** The user wants the one conviction bet (no
  count given). End in exactly one pick → `OUT/final_pick.md`. Use **Phase 3
  (single-pick variant)** + **Phase 4A**.
- **Ranked top-N mode.** The user asks to "rank", "top 5 / top 10", "give me N
  names", etc. Parse **N** (if they say "rank" with no number, default
  **N = 10**; cap N at the shortlist size). End in a ranked top-N →
  `OUT/final_ranking.md`. Use **Phase 3 (ranked variant)** + **Phase 4B**.
- **Optional multi-round aggregation** (ranked mode). If the user asks to run
  the panel several times and aggregate (e.g. "rank 5 times", "20 agents",
  "average it"), set **R** = the number of rounds (default R = 1) and repeat
  Phase 3 R times — i.e. **4×R** ranking agents total — then aggregate all 4×R
  ballots in Phase 4B. This cuts single-sample variance; call out where the
  averaged order differs from a single round.

If the mode is genuinely ambiguous, default to single-pick but tell the user
the ranked option exists (and vice-versa). State which mode (and N, R) you're
running before Phase 3.

---

## Phase 0 — Ensure the shortlist exists

The screen output lives at `OUT/shortlist.json` (and `OUT/shortlist.csv`).
**Build it yourself** — do not ask the user to run the pipeline.

1. **1-day cache check.** Read the `generated` timestamp inside
   `OUT/shortlist.json` (format `YYYY-MM-DD HH:MM:SS`). The screen is
   considered fresh if that timestamp is **less than 24 hours ago**.
   - If fresh (and the user didn't explicitly ask to refresh) → reuse it, skip
     straight to step 2.
   - If missing, stale (≥24h), or the user asked to refresh → rebuild it now by
     running **both** commands yourself, in order:
     ```bash
     uv run python scripts/fetch.py && uv run python scripts/screen.py --mode <MODE>
     ```
     `fetch.py` is itself cache-gated (prices ~1 day, info ~3 days,
     fundamentals ~7 days) so a rebuild within the week is fast — the slow path
     is only the first run of the week. If `uv` isn't available, fall back to
     `python scripts/...`. Tell the user you're (re)building the screen and
     roughly how long it takes (~2 min warm, up to ~10 min cold).
2. Read `OUT/shortlist.json` — ~30-50 candidates, each with ticker, security,
   GICS sector & sub-industry, marketCap, growth (rev_growth_ttm /
   revenueGrowth), operatingMargins, returnOnEquity, net_debt_ebitda, the price
   signals (dist_sma200, dist_52w_high, ret_12m), analyst_upside, valuation
   (trailingPE/forwardPE), and composite_score.
3. Briefly summarize to the user: how many candidates, the sector spread, and
   the top few by composite score (in dip mode, also the typical drawdown
   depth).

---

## Phase 1 — Triage to ~12-15 names

Web-researching the full shortlist deeply is wasteful. Score each candidate on
the **skill's triage criteria** using your own knowledge plus the metrics
already in the file (and a few quick `WebSearch` queries if unsure). Keep the
**top ~12-15** with the strongest doctrine narrative. Tell the user the
shortlist and a one-line rationale each. Drop the rest — and note honestly why
a couple of high-composite names were dropped if they lack the doctrine angle.

---

## Phase 2 — Deep web research (parallel research subagents)

Split the ~12-15 names into 3-4 batches and spawn one **research subagent per
batch** in parallel (single message, multiple `Agent` calls; model per the
subagent policy above). Give each subagent the **skill's research brief** with
its batch of tickers filled in.

Collect the returned dossiers. Assemble a single consolidated **research
dossier** (markdown) covering all ~12-15 names with their metrics + findings +
scores. Save it to `OUT/research_dossier.md`.

---

## Phase 3 — Independent nomination / ranking (the voting panel)

Spawn **4 independent selection subagents** in parallel (one message, four
`Agent` calls). Give all four the **same** consolidated dossier, but assign
each one of the **skill's four lenses** so the panel isn't an echo chamber.
**In ranked top-N mode with R > 1, spawn 4×R agents** (R independent rounds of
the four lenses) — parallelize as far as is practical (batch the messages if
4×R is large).

- **Single-pick variant** — each subagent returns the skill's single-pick
  ballot, in exactly that structure.
- **Ranked variant** — each subagent **ranks its top max(N, 10)** of the
  shortlisted names, best first, through its lens (rank a floor of 10 even when
  N < 10 so the aggregate has depth below the cut line), using the skill's
  ranked-ballot format so the ballots aggregate cleanly.

---

## Phase 3.5 — Verify the winner's load-bearing claims

The four panelists all read the *same* dossier, so an error there propagates to
every ballot — check it before publishing. After tentatively deciding the
winner (Phase 4A) or the top 3 (Phase 4B), and **before writing the final
file**, spawn **one verifier subagent** (same model policy) with this brief:

> Independently verify these specific claims via web search, from primary
> sources where possible (earnings calls, 10-Q/10-K, company PRs, reputable
> financial press). For each claim answer CONFIRMED / CONTRADICTED / UNVERIFIED
> with the source and date: [the 3-4 load-bearing claims per name — the
> headline evidence (backlog figure / why-it's-down cause), the catalyst and
> its date, the key valuation number, and the moat's central factual claim].

- All confirmed → proceed; note the verification in the writeup.
- A claim is **contradicted or unverifiable** → correct the dossier, tell the
  user, and re-adjudicate Phase 4 with the corrected fact. If the winner
  changes, verify the new winner too. Never publish a pick whose headline
  evidence failed verification.

Verify only the winner (single-pick) or the top 3's headline claims (ranked) —
that keeps the cost trivial while catching the errors that matter.

---

## Phase 4A — Aggregate and pick ONE (single-pick mode)

You (the orchestrator) now decide. Do NOT just count votes mechanically:

1. Tally each agent's top pick and runner-up (weight top pick 2, runner-up 1).
2. Where agents disagree, read their reasoning and adjudicate on the merits —
   the strongest, freshest doctrine evidence wins ties; a thesis the market has
   already fully priced loses to one with room to surprise.
3. **Apply the skill's trap filter — it can veto the vote.** A name with a
   *credible* trap threat is a poor bet even if it wins the vote. Treat high
   trap risk as a near-disqualifier; prefer the name the trap cannot touch.
4. Sanity-check the winner against the hard data in `OUT/shortlist.json` (it
   must still pass the doctrine — don't override the screen).
5. Run **Phase 3.5 verification** on the tentative winner.
6. Choose **exactly one** final pick.

Write `OUT/final_pick.md` with these **common sections**, interleaved with the
skill's doctrine-specific sections where its SKILL.md says:

- **THE PICK:** ticker, company, sector/sub-industry, current market cap.
- **One-paragraph thesis** in plain language.
- *(the skill's doctrine-specific evidence sections)*
- **Return scenario + price targets:** base vs bull case over 12-18 months,
  with the reasoning. Include an explicit **price-target table** with the
  current price, a **base-case target (price + % + by when)**, a **bull-case
  target (price + % + by when)**, and a **downside / thesis-break exit price**.
  Derive the targets from the scenario %s and anchor them to the current price
  and the analyst mean target in `shortlist.json` — and if the stock trades
  *above* the analyst mean target, say so honestly. Label every number a
  research scenario, not a guarantee.
- **Holding period & exit plan** — a recommended hold horizon and *why*, tied
  to the thesis/catalyst timeline. **Pair the price targets with the timing:**
  "base target $X by ~<date/quarter>; bull target $Y by ~<date> if <catalyst>;
  exit if it hits the downside trigger price $Z or any thesis-break trigger
  fires." Give concrete **thesis-break exit triggers** — observable events
  meaning "sell now, the story changed" (the skill's doctrine defines what
  these look like). Then a **leverage-safety note**: how the name's
  volatility/cyclicality should temper any use of leverage. Frame this as risk
  education, NOT a personalized leverage recommendation — never suggest a
  specific leverage ratio or position size.
- **Key risks** and what would invalidate the thesis (the trap case).
- **What was verified** — the Phase 3.5 claims and their outcomes.
- **The panel:** each agent's pick + conviction, and how you adjudicated.
- **Screen metrics** for the pick (from shortlist.json).
- A dated disclaimer: this is research output, not financial advice.

Then **record the pick in the ledger** (see Ledger below), and present a tight
summary to the user: the pick, the one-line thesis, the panel vote, and the
headline return scenario. Point them to the full writeup.

---

## Phase 4B — Aggregate into a ranked top-N (ranked mode)

You (the orchestrator) now build the ranking. Aggregate, then adjudicate:

1. **Score the ballots with Borda points.** Within each agent's ranked list,
   rank 1 = 10 pts, rank 2 = 9, … rank 10 = 1 (unranked = 0). Sum across all
   ballots (4 agents, or **4×R** if you ran R rounds). Per name also track:
   **appearances** (how many ballots ranked it), **#1 votes**, and **average
   placement** — these separate *conviction* (many #1 votes) from *consensus*
   (ranked by almost everyone but rarely at the top).
2. **Order by total Borda.** Break ties on the doctrine, not mechanically:
   stronger, fresher doctrine evidence wins; then more #1 votes, then better
   average placement.
3. **The trap is a FLAG here, not a veto.** Unlike single-pick mode, in a
   ranking you **keep** trap-suspect names but make the risk visible in their
   row — the reader sees the caveat and decides. Note explicitly if the
   strict-doctrine order at the top would differ from the Borda order.
4. Sanity-check every top-N name against `OUT/shortlist.json` (each must still
   pass the screen's doctrine — don't override the screen).
5. Run **Phase 3.5 verification** on the top 3's headline claims.
6. Produce the final ranked **top N**.

Write `OUT/final_ranking.md` with:

- **The ranking table** — rank, ticker, company, sector/sub-industry, current
  price, analyst mean target (+upside %), forward PE, the **skill's doctrine
  scores** (and in dip mode the dip depth `dist_52w_high`), and a one-line case
  per name. If you ran R > 1 rounds, also show **Borda points, appearances
  (e.g. 16/20), #1 votes, and average placement**.
- **Per-name thesis** — a one-paragraph thesis for at least the top 3–5 (the
  skill defines what it must cover); one tight line each for the rest.
- **Just-missed names** — the few that fell just outside the top N, with why.
- **What the panel revealed** — each lens's top few, where they
  agreed/disagreed, and (if R > 1) which names were conviction vs consensus,
  and what the averaging changed vs a single round.
- **If forced to ONE** — the single pick the strict trap-veto would land on,
  and why it may differ from the Borda #1. This keeps the doctrine honest even
  in ranked mode.
- **Return scenarios** — at minimum a base/bull headline for the top 3,
  anchored to current price and the analyst mean target in `shortlist.json`;
  flag any name trading *above* its mean target. Label every number a research
  scenario, not a guarantee.
- **What was verified** — the Phase 3.5 claims and their outcomes.
- **Risk lens & leverage-safety note** across the list — sector concentration,
  which names are highest-risk vs steadier compounders, paired with drawdown
  reality. Education-not-advice framing: never a specific leverage multiple or
  position size.
- **Thesis-break / trap triggers** to watch across the ranked names.
- A dated disclaimer: this is research output, not financial advice.

Then **record the top N in the ledger** (see Ledger below), and present a tight
summary: the ranked table, the panel split (and what multi-round averaging
changed, if R > 1), and point the user to the writeup.

---

## Ledger — every pick gets recorded

`picks/ledger.csv` is the project's scorecard input (scored by
`scripts/scorecard.py`). After writing the final file, append one row per pick
(one row in single-pick mode; N rows in ranked mode). Columns:

```
date,mode,kind,rank,ticker,price_at_pick,base_target,base_by,bull_target,bull_by,exit_price,thesis,source
```

- `date` — today, YYYY-MM-DD. `mode` — momentum|dip. `kind` — single|rankN
  (e.g. rank10). `rank` — 1 for single mode.
- `price_at_pick` — the current price from `shortlist.json`.
- `base_target`/`bull_target` + `base_by`/`bull_by` (YYYY-MM or a quarter) and
  `exit_price` — from the writeup's price-target table; leave empty for ranked
  names below the top 3 if no scenario was written.
- `thesis` — one line, CSV-quoted. `source` — the writeup path.

Create the file with the header if it doesn't exist. Never rewrite or delete
existing rows — the ledger is append-only history.

---

## Guardrails

- **Never fabricate** financial figures, backlog/drawdown numbers, valuation
  multiples, or quotes. Attribute and date every concrete claim; if research
  can't confirm something, say so. Phase 3.5 exists to enforce this — never
  skip it.
- **Respect the chosen mode.** Single-pick mode → **exactly one** final pick
  (the point is forcing a decision; the trap filter can veto the vote). Ranked
  mode → **exactly N** names (default 10), ordered, with each name's trap
  caveat visible rather than vetoed.
- Don't override the deterministic screen. If you think a gate is wrong, say so
  to the user, but pick (or rank) from the screened set.
- **Leverage:** you may explain how a name's volatility/cyclicality affects
  leverage *risk* (education), but never recommend a specific leverage multiple
  or position size — that's personalized advice. Always pair any leverage
  discussion with the drawdown reality.
- This is research/education, not personalized investment advice. Always
  include the disclaimer.

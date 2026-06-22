---
name: stock-pick
description: Pick ONE S&P 500 stock with explosive-return potential from the deterministic screen. Runs the Python funnel to get ~50 quality category-leaders, web-researches each for structural-shortage / order-book-backlog signals, fans the enriched dossier out to multiple Opus 4.8 subagents that independently nominate, then aggregates into one final conviction pick with a written thesis. Use when the user asks to "pick a stock", "run the stock picker", "find the next MU", or invokes /stock-pick.
---

# Stock Pick — from S&P 500 to one conviction bet

You are orchestrating a funnel that ends in **exactly one** stock pick. The
philosophy (modeled on a friend's early MU call): a great explosive-return bet
is **a profitable US company that is the biggest in its niche and is riding a
structural shortage** — demand the world cannot supply fast enough, with a
backlog/order book that gives multi-year revenue visibility (MU's HBM booked
out to 2026/2027 was the tell).

The deterministic Python screen has already enforced *profitable + US + growing
+ low-debt + momentum + margin-leader + category #1*. Your job is the part code
can't do: **read the world** for the shortage/backlog signal, then force a
decision through independent AI deliberation.

Work through the phases in order. Keep the user updated between phases.

---

## Phase 0 — Ensure the shortlist exists

The screen output lives at `output/shortlist.json` (and `output/shortlist.csv`).

1. Check whether `output/shortlist.json` exists and is recent (regenerate if the
   user asks, or if it's missing/older than ~5 days). To build/refresh it:
   ```bash
   uv run python scripts/fetch.py      # ~5-10 min first run; cached after
   uv run python scripts/screen.py     # writes output/shortlist.json
   ```
   (If `uv` isn't set up, fall back to `python`.)
2. Read `output/shortlist.json`. It has ~50 candidates, each with: ticker,
   security, GICS sector & sub-industry, marketCap, revenueGrowth,
   operatingMargins, returnOnEquity, net_debt_ebitda, momentum (dist_sma200,
   ret_12m), analyst_upside, valuation (trailingPE/forwardPE), composite_score.
3. Briefly summarize to the user: how many candidates, the sector spread, and
   the top few by composite score.

---

## Phase 1 — Triage to the shortage shortlist (~12-15 names)

Web-researching 50 names deeply is wasteful. First narrow to the names with a
*plausible structural-shortage or backlog thesis*. Using your own knowledge plus
the metrics already in the file (and a few quick `WebSearch` queries if unsure),
score each of the ~50 on:

- **Shortage potential** — is its product/service supply-constrained or in a
  demand surge it can't easily meet? (AI compute, HBM/memory, power & grid,
  electrical equipment, datacenter cooling, nuclear/uranium, defense, specific
  drugs, mining, niche semis/equipment, etc.)
- **Backlog / order-book visibility** — does it report a large or growing
  backlog, multi-year bookings, "sold out" capacity, or take-or-pay contracts?
- **Category dominance** — is it the clear #1 with pricing power (the screen
  already favored this, but weight it).

Keep the **top ~12-15** with the strongest shortage/backlog narrative. Tell the
user the shortlist and one-line rationale each. Drop the rest (note why a couple
of high-composite names were dropped if they lack a shortage angle — be honest).

---

## Phase 2 — Deep web research (parallel research subagents)

Split the ~12-15 names into 3-4 batches and spawn one **research subagent per
batch** in parallel (single message, multiple `Agent` calls). Use
`subagent_type: "claude"` with `model: "opus"`.

Give each research subagent this brief (fill in its batch of tickers):

> Research these S&P 500 companies as candidates for an explosive-return bet:
> [TICKERS + company names]. For EACH, use web search to gather and report:
> 1. **Shortage thesis** — is its core product/service in structural shortage or
>    a demand surge supply can't meet? Cite the specific driver (e.g. AI
>    datacenter buildout, grid electrification, GLP-1 demand). Quote concrete
>    evidence (capacity sold out, lead times extending, price increases).
> 2. **Backlog / order book** — latest reported backlog or bookings figure,
>    growth rate, and how far out it's booked. Quote the number and source date.
> 3. **Category position** — is it the #1 player? market share vs #2?
> 4. **Recent catalysts** (last ~3 months) — earnings beats, capacity
>    expansions, big contracts/design wins, guidance raises, analyst upgrades.
> 5. **Risks** — what could break the thesis (cyclicality, competition,
>    customer concentration, valuation already pricing it in).
> 6. **Shortage score 0-10** and **one-sentence verdict** per company.
> Return a compact dossier per ticker. Prefer primary sources (earnings calls,
> 10-Q/10-K, company PRs) and reputable financial press; include dates. Do not
> fabricate numbers — if you can't find a figure, say "not found".

Collect the returned dossiers. Assemble a single consolidated **research
dossier** (markdown) covering all ~12-15 names with their metrics + findings +
shortage scores. Save it to `output/research_dossier.md`.

---

## Phase 3 — Independent nomination (Opus 4.8 voting panel)

Spawn **4 independent selection subagents** in parallel (one message, four
`Agent` calls, `subagent_type: "claude"`, `model: "opus"`). Give all four the
**same** consolidated dossier, but assign each a distinct lens so the panel
isn't an echo chamber:

- **Agent A — Supply-chain analyst:** weight the shortage/backlog evidence and
  multi-year revenue visibility above all.
- **Agent B — Growth/momentum investor:** weight revenue acceleration, earnings
  revisions, and price momentum; wants the fastest compounder.
- **Agent C — Quality/moat investor:** weight category dominance, margins,
  returns on capital, balance-sheet durability, and durability of the thesis.
- **Agent D — Contrarian/risk skeptic:** hunt for the thesis that is *real but
  still underappreciated by the market* (avoid what's already fully priced);
  explicitly weigh valuation and downside.

Each subagent must return, in this exact structure:
> - **Top pick:** TICKER
> - **Runner-up:** TICKER
> - **Thesis (3-5 sentences):** why this one has explosive upside
> - **Key shortage/backlog evidence:** the single most compelling data point
> - **12-18 month return scenario:** rough base / bull case
> - **Top risk:**
> - **Conviction (1-10):**

---

## Phase 4 — Aggregate and pick ONE

You (the orchestrator) now decide. Do NOT just count votes mechanically:

1. Tally each agent's top pick and runner-up (weight top pick 2, runner-up 1).
2. Where agents disagree, read their reasoning and adjudicate on the merits —
   strength and recency of the shortage/backlog evidence wins ties; a thesis the
   market has already fully priced loses to one with room to surprise.
3. Sanity-check the winner against the hard data in `shortlist.json` (it must
   still pass the doctrine — don't override the screen).
4. Choose **exactly one** final pick.

Write `output/final_pick.md` with:
- **THE PICK:** ticker, company, sector/sub-industry, current market cap.
- **One-paragraph thesis** in plain language (the "why this is the next MU").
- **The shortage + backlog evidence** (the concrete, sourced data points).
- **Why it's the category leader.**
- **Return scenario:** base vs bull case over 12-18 months, with the reasoning.
- **Key risks** and what would invalidate the thesis.
- **The panel:** each agent's pick + conviction, and how you adjudicated.
- **Screen metrics** for the pick (pull from shortlist.json).
- A dated disclaimer: this is research output, not financial advice.

Then present a tight summary to the user: the pick, the one-line thesis, the
panel vote, and the headline return scenario. Point them to the full writeup in
`output/final_pick.md`.

---

## Guardrails

- **Never fabricate** financial figures, backlog numbers, or quotes. Attribute
  and date every concrete claim; if research can't confirm something, say so.
- **Exactly one** final pick — the whole point is forcing a decision.
- Don't override the deterministic screen. If you think a gate is wrong, say so
  to the user, but pick from the screened set.
- This is research/education, not personalized investment advice. Always include
  the disclaimer.

---
name: stock-pick-momentum
description: Pick ONE S&P 500 momentum stock with explosive-return potential — or a ranked top-N — from the deterministic MOMENTUM screen (price above its 200-day SMA, riding a structural shortage). Runs the Python funnel in --mode momentum to get ~50 quality category-leaders, web-researches each for structural-shortage / order-book-backlog signals, fans the enriched dossier out to multiple Opus 4.8 subagents that independently nominate (or rank), then aggregates into either one final conviction pick or a ranked top-N with a written thesis. Use when the user asks to "pick a momentum stock", "run the momentum picker", "find the next MU", "rank the top N momentum stocks", or invokes /stock-pick-momentum. For beaten-down quality names that will rebound, use the sibling /stock-pick-dip skill instead.
---

# Stock Pick (Momentum) — from S&P 500 to a conviction bet (one pick, or a ranked top-N)

> Buys **strength**: this skill rides the deterministic momentum screen (price
> **above** its 200-day SMA) plus a structural-shortage thesis. The mirror-image
> skill **`stock-pick-dip`** buys **weakness** — quality names that have
> corrected and will rebound. Same funnel, opposite price gate.

**First, read `.claude/skills/shared/pick-protocol.md`** — it defines the whole
machinery (mode selection, Phase 0 shortlist build, triage, research fan-out,
the voting panel, Phase 3.5 verification, Phase 4A/4B aggregation, the picks
ledger, and the guardrails). Execute that protocol with these parameters and
the doctrine below:

- **MODE:** `momentum` → `OUT = output/momentum/`, screen command
  `uv run python scripts/fetch.py && uv run python scripts/screen.py --mode momentum`
- **THE TRAP (the protocol's veto/flag):** disintermediation / in-sourcing —
  defined below.

Everything below is the momentum doctrine — the content the protocol's phases
consume.

---

## The doctrine

The philosophy (modeled on a friend's early MU call): a great explosive-return
bet is **a profitable US company that is the biggest in its niche, is riding a
structural shortage, AND owns technology that cannot easily be replaced or
in-sourced** — demand the world cannot supply fast enough, with a backlog/order
book that gives multi-year revenue visibility (MU's HBM booked out to 2026/2027
was the tell), sold by a company its own customers *can't* simply become.

The deterministic Python screen has already enforced *profitable + US + growing
+ low-debt + momentum + margin-leader + category #1*. Your job is the part code
can't do: **read the world** for (a) the shortage/backlog signal and (b) the
**irreplaceability / disintermediation risk**, then force a decision through
independent AI deliberation.

**The disintermediation trap (weight this heavily — this is THE TRAP).** A
supplier can look unstoppable while it is structurally doomed: a hot vendor
booms, then its largest customers — especially hyperscalers — build the thing
themselves (custom ASICs vs NVDA, in-house cloud silicon, private-label,
vertical integration) and the revenue collapses and *never comes back*. The
best explosive-return bet is one whose product the customer **cannot**
replicate: protected by process-tech leads, patents,
certification/qualification lock-in, extreme capital intensity, or a
sub-scale-uneconomic-to-copy moat. Only ~3 firms on earth can make HBM; a
hyperscaler can in-source a chip design far more easily than a memory fab —
that asymmetry is exactly what this criterion hunts.

---

## Phase 1 triage criteria (keep the ~12-15 strongest)

- **Shortage potential** — is its product/service supply-constrained or in a
  demand surge it can't easily meet? (AI compute, HBM/memory, power & grid,
  electrical equipment, datacenter cooling, nuclear/uranium, defense, specific
  drugs, mining, niche semis/equipment, etc.)
- **Backlog / order-book visibility** — does it report a large or growing
  backlog, multi-year bookings, "sold out" capacity, or take-or-pay contracts?
- **Category dominance** — is it the clear #1 with pricing power (the screen
  already favored this, but weight it).
- **Irreplaceability / disintermediation risk** — could its biggest customers
  (especially hyperscalers) realistically build or in-source this themselves,
  or could a substitute technology bypass it? Favor names protected by
  process-tech leads, patents, certification lock-in, or prohibitive capital
  intensity; be wary of vendors whose customers are *already* building their
  own version.

---

## Phase 2 research brief (per batch of tickers)

> Research these S&P 500 companies as candidates for an explosive-return bet:
> [TICKERS + company names]. For EACH, use web search to gather and report:
> 1. **Shortage thesis** — is its core product/service in structural shortage or
>    a demand surge supply can't meet? Cite the specific driver (e.g. AI
>    datacenter buildout, grid electrification, GLP-1 demand). Quote concrete
>    evidence (capacity sold out, lead times extending, price increases).
> 2. **Backlog / order book** — latest reported backlog or bookings figure,
>    growth rate, and how far out it's booked. Quote the number and source date.
> 3. **Category position** — is it the #1 player? market share vs #2?
> 4. **Irreplaceability / disintermediation risk** — can its biggest customers
>    (especially hyperscalers) realistically build or in-source this themselves,
>    or could a substitute technology route around it? Name the moat that
>    prevents it (process-tech lead, patents, certification/qualification
>    lock-in, capital intensity, # of firms on earth that can make it) OR the
>    concrete in-sourcing threat (e.g. customers shipping their own ASICs).
>    Quote evidence and give an **irreplaceability score 0-10** (10 = nobody can
>    replicate or bypass it).
> 5. **Recent catalysts** (last ~3 months) — earnings beats, capacity
>    expansions, big contracts/design wins, guidance raises, analyst upgrades.
> 6. **Risks** — what could break the thesis (cyclicality, competition,
>    customer concentration, in-sourcing, valuation already pricing it in).
> 7. **Shortage score 0-10** and **one-sentence verdict** per company.
> Return a compact dossier per ticker. Prefer primary sources (earnings calls,
> 10-Q/10-K, company PRs) and reputable financial press; include dates. Do not
> fabricate numbers — if you can't find a figure, say "not found".

---

## Phase 3 — the four lenses

- **Agent A — Supply-chain analyst:** weight the shortage/backlog evidence and
  multi-year revenue visibility above all.
- **Agent B — Growth/momentum investor:** weight revenue acceleration, earnings
  revisions, and price momentum; wants the fastest compounder.
- **Agent C — Quality/moat & irreplaceability investor:** weight category
  dominance, margins, returns on capital, balance-sheet durability, and above
  all **irreplaceability** — reject any name whose customers (especially
  hyperscalers) could realistically build or in-source the product themselves,
  or that a substitute technology could route around. You want a moat nobody can
  copy.
- **Agent D — Contrarian/risk skeptic:** hunt for the thesis that is *real but
  still underappreciated by the market* (avoid what's already fully priced);
  explicitly weigh valuation, downside, and disintermediation risk.

**Single-pick ballot** — each subagent must return, in this exact structure:
> - **Top pick:** TICKER
> - **Runner-up:** TICKER
> - **Thesis (3-5 sentences):** why this one has explosive upside
> - **Key shortage/backlog evidence:** the single most compelling data point
> - **Irreplaceability / disintermediation risk:** can a customer/hyperscaler
>   in-source or a substitute bypass it? (low / medium / high — and why)
> - **12-18 month return scenario:** rough base / bull case
> - **Top risk:**
> - **Conviction (1-10):**

**Ranked ballot** — per the protocol's ranked variant:
> A numbered list, best first: `RANK. TICKER — <=6-word reason (this lens)`.
> Then, for its **top 3 only**, 2–3 sentences on the single most compelling
> shortage/backlog or moat data point and a rough 12–18mo base/bull scenario.
> Then one line: which names it deliberately left out of its top 10 and why.

---

## Doctrine-specific sections of the final writeup

In `final_pick.md`, between the thesis and the return scenario (see the
protocol's common template), include:

- **The shortage + backlog evidence** (the concrete, sourced data points).
- **Why it's the category leader.**
- **Why it's irreplaceable** — the moat that stops a customer/hyperscaler from
  in-sourcing it or a substitute from bypassing it (or an honest statement of
  the disintermediation risk if it's the pick's main weakness).

Thesis-break exit triggers here look like: backlog shrinking, pricing rolling
over, margins peaking QoQ, a customer announcing in-sourcing. The
leverage-safety note should reflect that a high-beta cyclical (like memory) can
draw down 50%+ fast, which is brutal with margin.

In `final_ranking.md`, the ranking table's doctrine scores are the **shortage
score** and **irreplaceability score**; each top-3-5 thesis paragraph must
cover the shortage + backlog evidence, why it's the category leader, and the
moat OR the honest disintermediation caveat.

Phase 3.5 verification targets for this doctrine: the backlog/bookings figure,
the shortage-driver claim, the catalyst and its date, and the moat's central
factual claim (e.g. "only ~3 firms can make HBM").

---
name: stock-pick-dip
description: Pick ONE S&P 500 quality stock that has dipped and will rebound — or a ranked top-N — from the deterministic DIP screen (price below its 200-day SMA but not wrecked, moaty, profitable, still growing). Runs the Python funnel in --mode dip to get ~40 corrected category-leaders, web-researches each for whether the drop is temporary vs permanent, the moat / AI-irreplaceability, a rebound catalyst, balance-sheet survival, and margin of safety, fans the dossier out to multiple Opus 4.8 subagents that independently nominate (or rank), then aggregates into one final conviction pick or a ranked top-N with a written thesis. Use when the user asks to "buy the dip", "find a reboundable dip", "pick a quality dip", "rank N dips", or invokes /stock-pick-dip. For names already trending up on a structural shortage, use the sibling /stock-pick-momentum skill instead.
---

# Stock Pick (Dip) — buy a reboundable quality dip (one pick, or a ranked top-N)

> Buys **weakness**: this skill rides the deterministic dip screen (price
> **below** its 200-day SMA, off its 52-week high but not wrecked) and looks for
> a quality compounder dislocated *temporarily*. The mirror-image skill
> **`stock-pick-momentum`** buys **strength** — names trending up on a
> structural shortage. Same funnel, opposite price gate.

**First, read `.claude/skills/shared/pick-protocol.md`** — it defines the whole
machinery (mode selection, Phase 0 shortlist build, triage, research fan-out,
the voting panel, Phase 3.5 verification, Phase 4A/4B aggregation, the picks
ledger, and the guardrails). Execute that protocol with these parameters and
the doctrine below:

- **MODE:** `dip` → `OUT = output/dip/`, screen command
  `uv run python scripts/fetch.py && uv run python scripts/screen.py --mode dip`
- **THE TRAP (the protocol's veto/flag):** the value trap / permanent
  impairment — defined below.

Everything below is the dip doctrine — the content the protocol's phases
consume.

---

## The doctrine

The philosophy: a great dip-buy is **a profitable US company that is the
biggest in its niche and owns a moat that cannot easily be replaced —
especially one AI or a substitute cannot disrupt — whose stock has corrected
hard for a *transitory* reason** (macro, sentiment, sector rotation, a one-off
miss, a cyclical trough) rather than a permanent impairment, with an
identifiable **rebound catalyst**, a balance sheet that comfortably
**survives** the drawdown, and a genuine **margin of safety** vs its own
history. You buy the dislocation, not the decline.

The deterministic Python screen has already enforced *profitable + US + growing
+ low-debt + IN A DIP (below 200-day SMA, drawdown within the floor) +
margin-leader + cheap-enough-forward-PE + category #1*. Your job is the part
code can't do: **read the world** for (a) whether the dip is temporary or
permanent and (b) the **moat / AI-irreplaceability**, then force a decision
through independent AI deliberation.

**The value-trap / falling-knife trap (weight this heavily — this is THE
TRAP).** A stock can look cheap and oversold while it is structurally doomed: a
once-great franchise gets disrupted (AI eats its product, a platform shift
routes around it, a secular demand decline sets in) and the price falls and
falls — and the "dip" never recovers because the *business* is impaired, not
just the sentiment. The best dip-buy is one whose moat is fully intact and
whose drop is provably about *price, not the business*: protected by switching
costs, network effects, process-tech / patents, certification lock-in, brand,
or capital intensity that AI and new entrants cannot erode. Distinguishing a
temporary dislocation from a permanent impairment is the single most important
judgment in this skill — it is the dip mirror of the momentum skill's
disintermediation trap.

---

## Phase 1 triage criteria (keep the ~12-15 strongest)

- **Dip shape & cause** — how deep is the drawdown (`dist_52w_high`,
  `dist_sma200`), and is the drop driven by something *transitory* (macro/rate
  fears, a sentiment swing, sector rotation, a one-off earnings miss, a cyclical
  trough) versus a *permanent* impairment (lost moat, secular decline, a product
  AI/new tech is disrupting)?
- **Moat / AI-irreplaceability** — is the franchise durable and hard to replace,
  and crucially can **AI or a substitute technology** route around or
  commoditize its product? Favor switching costs, network effects,
  process-tech/patents, certification lock-in, brand, capital intensity; be wary
  of anything AI could disintermediate.
- **Rebound catalyst** — is there a concrete path back up (earnings recovery,
  cycle turn, new product cycle, buyback, guidance reset, margin inflection,
  cost-out, an activist, a sentiment normalization)?
- **Balance-sheet survival** — low debt, positive FCF, cash — can it comfortably
  endure the drawdown without distress or dilution?
- **Margin of safety** — has the dip made it genuinely cheap vs its own history
  and peers (forward PE, the analyst mean target upside), so downside is
  limited?

When dropping names, note honestly why a couple of deep-discount names were cut
if they look like value traps / permanent impairment.

---

## Phase 2 research brief (per batch of tickers)

> Research these S&P 500 companies as candidates for a buy-the-dip rebound bet
> (each has already corrected — it trades below its 200-day SMA and off its
> 52-week high): [TICKERS + company names]. For EACH, use web search to gather
> and report:
> 1. **Why it's down** — what drove the drawdown over the last 3-12 months? Is
>    the cause **transitory** (macro/rates, sentiment, sector rotation, a one-off
>    miss, a cyclical trough) or a **permanent impairment** (lost moat, secular
>    demand decline, a product AI or a substitute is disrupting)? Quote concrete
>    evidence and dates. Give a **temporary-vs-permanent verdict**.
> 2. **Moat / AI-irreplaceability** — how durable is the franchise, and can AI or
>    a substitute technology route around or commoditize its product? Name the
>    moat (switching costs, network effects, process-tech/patents, certification
>    lock-in, brand, capital intensity) OR the concrete disruption threat. Give
>    an **irreplaceability score 0-10** (10 = AI/substitutes cannot touch it).
> 3. **Rebound catalyst** — the concrete path back up and rough timing (earnings
>    recovery, cycle turn, new product, buyback, guidance reset, margin
>    inflection, activist, sentiment reset). Quote evidence and dates.
> 4. **Balance-sheet survival** — net debt / leverage, FCF, cash. Can it endure
>    the drawdown without distress or dilution?
> 5. **Margin of safety / valuation** — current forward P/E vs its own multi-year
>    history and peers; the analyst mean target and implied upside. Is it genuinely
>    cheap *because of the dip*, or still expensive? Quote numbers and source dates.
> 6. **Category position** — is it still the #1 player with pricing power, or is
>    the dip a sign share is being lost?
> 7. **Value-trap risk** — the honest bear case: what would make this a falling
>    knife that never recovers.
> 8. **Rebound score 0-10** and **one-sentence verdict** per company.
> Return a compact dossier per ticker. Prefer primary sources (earnings calls,
> 10-Q/10-K, company PRs) and reputable financial press; include dates. Do not
> fabricate numbers — if you can't find a figure, say "not found".

---

## Phase 3 — the four lenses

- **Agent A — Mean-reversion / catalyst analyst:** weight the strength and timing
  of the rebound catalyst and the evidence that the drop is *temporary* above all;
  wants the name most likely to re-rate fastest.
- **Agent B — Growth/quality compounder investor:** weight revenue durability,
  margins, returns on capital, and that the dip hasn't broken the growth story;
  wants a great business bought on sale.
- **Agent C — Moat & AI-irreplaceability investor:** weight category dominance,
  balance-sheet durability, and above all **irreplaceability** — reject any name
  whose product **AI or a substitute technology** could realistically disrupt or
  commoditize, or whose moat the dip reveals is eroding. You want a moat nobody
  (and no model) can copy.
- **Agent D — Falling-knife / value-trap skeptic:** hunt for permanent impairment
  hiding as a cheap dip; explicitly weigh whether the business (not just the
  price) is broken, the debt/survival risk, and whether the cheapness is a trap.
  This is the veto lens.

**Single-pick ballot** — each subagent must return, in this exact structure:
> - **Top pick:** TICKER
> - **Runner-up:** TICKER
> - **Thesis (3-5 sentences):** why this dip rebounds with explosive upside
> - **Why the dip is temporary (not permanent):** the single most compelling
>   evidence the drop is about price, not the business
> - **Moat / AI-irreplaceability:** can AI or a substitute disrupt it? (low /
>   medium / high risk — and why)
> - **Rebound catalyst & timing:** the concrete trigger and rough when
> - **12-18 month return scenario:** rough base / bull case
> - **Top risk (value-trap case):**
> - **Conviction (1-10):**

**Ranked ballot** — per the protocol's ranked variant:
> A numbered list, best first: `RANK. TICKER — <=6-word reason (this lens)`.
> Then, for its **top 3 only**, 2–3 sentences on the single most compelling
> temporary-dip + intact-moat (or rebound-catalyst) data point and a rough
> 12–18mo base/bull scenario. Then one line: which names it deliberately left
> out of its top 10 and why (flag any it suspects are value traps).

---

## Doctrine-specific sections of the final writeup

In `final_pick.md`, between the thesis and the return scenario (see the
protocol's common template), include:

- **Why the dip is temporary, not permanent** — the concrete, sourced evidence
  that the drop is about price/sentiment/cycle, not a broken business.
- **The dip depth** — how far below its 200-day SMA and off its 52-week high
  (`dist_sma200`, `dist_52w_high`), with the cause.
- **Why it's the category leader / why the moat is intact** — and specifically
  **why AI or a substitute cannot disrupt it** (or an honest statement of the
  disruption risk if it's the pick's main weakness).
- **The rebound catalyst & timing** — the dated trigger(s) that re-rate it.

**Scenario drivers (for the protocol's bear/base/bull builds):** build the
three scenarios on the depressed driver recovering (or not) toward its
trailing baseline × the multiple. Bear = the value trap realized: the dip's
cause turns out permanent — impaired earnings power at a de-rated multiple
(what does the business earn if the "temporary" headwind is the new normal?).
Base = earnings normalize to the pre-dip trajectory and the multiple
mean-reverts partway to its own history. Bull = the catalyst fires on time
and the multiple fully re-rates. Weight bear higher when the earnings-quality
flags or a competitor's guidance hint at share loss rather than macro.

Thesis-break exit triggers here look like: the rebound catalyst slips or
cancels, the moat is breached, AI/a substitute lands the disruptive blow,
fundamentals keep deteriorating, the next leg down breaks the drawdown floor.
The leverage-safety note should reflect that a beaten-down name can keep
falling — "catching a knife" with margin is brutal; size for the possibility
the dip deepens before it turns.

In `final_ranking.md`, the ranking table's doctrine scores are the **dip depth
(`dist_52w_high`) and the rebound & irreplaceability scores**; each top-3-5
thesis paragraph must cover why the dip is temporary, the rebound catalyst, and
why the moat/AI-irreplaceability holds OR the honest value-trap caveat. The
risk lens should call out which names are deepest in their drawdown / most
likely to keep falling.

Phase 3.5 verification targets for this doctrine: the why-it's-down cause, the
rebound catalyst and its date, the key valuation claim (forward P/E vs
history), and the moat's central factual claim.

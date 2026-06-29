---
name: stock-pick-dip
description: Pick ONE S&P 500 quality stock that has dipped and will rebound — or a ranked top-N — from the deterministic DIP screen (price below its 200-day SMA but not wrecked, moaty, profitable, still growing). Runs the Python funnel in --mode dip to get ~40 corrected category-leaders, web-researches each for whether the drop is temporary vs permanent, the moat / AI-irreplaceability, a rebound catalyst, balance-sheet survival, and margin of safety, fans the dossier out to multiple Opus 4.8 subagents that independently nominate (or rank), then aggregates into one final conviction pick or a ranked top-N with a written thesis. Use when the user asks to "buy the dip", "find a reboundable dip", "pick a quality dip", "rank N dips", or invokes /stock-pick-dip. For names already trending up on a structural shortage, use the sibling /stock-pick-momentum skill instead.
---

# Stock Pick (Dip) — buy a reboundable quality dip (one pick, or a ranked top-N)

> Buys **weakness**: this skill rides the deterministic dip screen (price
> **below** its 200-day SMA, off its 52-week high but not wrecked) and looks for
> a quality compounder dislocated *temporarily*. The mirror-image skill
> **`stock-pick-momentum`** buys **strength** — names trending up on a structural
> shortage. Same funnel, opposite price gate.

You are orchestrating a funnel that ends in either **exactly one** stock pick
**or** a **ranked top-N** — the user chooses (see *Mode* below). The
philosophy: a great dip-buy is **a profitable US company that is the biggest in
its niche and owns a moat that cannot easily be replaced — especially one AI or
a substitute cannot disrupt — whose stock has corrected hard for a *transitory*
reason** (macro, sentiment, sector rotation, a one-off miss, a cyclical trough)
rather than a permanent impairment, with an identifiable **rebound catalyst**, a
balance sheet that comfortably **survives** the drawdown, and a genuine **margin
of safety** vs its own history. You buy the dislocation, not the decline.

The deterministic Python screen has already enforced *profitable + US + growing
+ low-debt + IN A DIP (below 200-day SMA, drawdown within the floor) +
margin-leader + cheap-enough-forward-PE + category #1*. Your job is the part code
can't do: **read the world** for (a) whether the dip is temporary or permanent
and (b) the **moat / AI-irreplaceability**, then force a decision through
independent AI deliberation.

**The value-trap / falling-knife trap (weight this heavily).** A stock can look
cheap and oversold while it is structurally doomed: a once-great franchise gets
disrupted (AI eats its product, a platform shift routes around it, a secular
demand decline sets in) and the price falls and falls — and the "dip" never
recovers because the *business* is impaired, not just the sentiment. The best
dip-buy is one whose moat is fully intact and whose drop is provably about
*price, not the business*: protected by switching costs, network effects,
process-tech / patents, certification lock-in, brand, or capital intensity that
AI and new entrants cannot erode. Distinguishing a temporary dislocation from a
permanent impairment is the single most important judgment in this skill — it is
the dip mirror of the momentum skill's disintermediation trap.

Work through the phases in order. Keep the user updated between phases.

---

## Mode — one final pick (default) or a ranked top-N

The funnel is **identical** in both modes through Phases 0–2; only Phase 3's
return format and Phase 4's output differ. Decide the mode from the user's
request / the `/stock-pick-dip` arguments:

- **Single-pick mode (DEFAULT).** The user wants the one conviction dip-buy
  ("buy the dip", "find a reboundable dip", no count given). End in exactly one
  pick → `output/dip/final_pick.md`. Use **Phase 3 (single-pick variant)** +
  **Phase 4A**.
- **Ranked top-N mode.** The user asks to "rank", "top 5 / top 10", "give me N
  names", "rank N instead of 1", etc. Parse **N** (if they say "rank" with no
  number, default **N = 10**; cap N at the shortlist size). End in a ranked top-N
  → `output/dip/final_ranking.md`. Use **Phase 3 (ranked variant)** + **Phase 4B**.
- **Optional multi-round aggregation** (ranked mode). If the user asks to run the
  panel several times and aggregate (e.g. "rank 5 times", "20 agents", "average
  it"), set **R** = the number of rounds (default R = 1) and repeat Phase 3 R
  times — i.e. **4×R** ranking agents total — then aggregate all 4×R ballots in
  Phase 4B. This cuts single-sample variance; call out where the averaged order
  differs from a single round.

If the mode is genuinely ambiguous, default to single-pick but tell the user the
ranked option exists (and vice-versa). State which mode (and N, R) you're running
before Phase 3.

---

## Phase 0 — Ensure the shortlist exists

The screen output lives at `output/dip/shortlist.json` (and
`output/dip/shortlist.csv`). **Build it yourself** — do not ask the user to run
the pipeline.

1. **1-day cache check.** Read the `generated` timestamp inside
   `output/dip/shortlist.json` (format `YYYY-MM-DD HH:MM:SS`). The screen is
   considered fresh if that timestamp is **less than 24 hours ago**.
   - If fresh (and the user didn't explicitly ask to refresh) → reuse it, skip
     straight to step 2.
   - If missing, stale (≥24h), or the user asked to refresh → rebuild it now by
     running **both** commands yourself, in order:
     ```bash
     uv run python scripts/fetch.py && uv run python scripts/screen.py --mode dip
     ```
     `fetch.py` is itself cache-gated (prices ~1 day, info ~3 days) so a rebuild
     within the week is fast — the slow path is only the first run of the week.
     If `uv` isn't available, fall back to `python scripts/...`. Tell the user
     you're (re)building the dip screen and roughly how long it takes (~2 min
     warm, up to ~10 min cold).
2. Read `output/dip/shortlist.json`. It has ~30-45 candidates, each with: ticker,
   security, GICS sector & sub-industry, marketCap, revenueGrowth,
   operatingMargins, returnOnEquity, net_debt_ebitda, the **dip signals**
   (`dist_sma200` — how far below the 200-day SMA; `dist_52w_high` — drawdown
   from the 52-week high), analyst_upside, valuation (trailingPE/forwardPE),
   composite_score (the rebound score).
3. Briefly summarize to the user: how many candidates, the sector spread, the
   typical drawdown depth, and the top few by composite (rebound) score.

---

## Phase 1 — Triage to the rebound shortlist (~12-15 names)

Web-researching 40 names deeply is wasteful. First narrow to the names with the
strongest *reboundable-dip thesis*. Using your own knowledge plus the metrics
already in the file (and a few quick `WebSearch` queries if unsure), score each
of the ~40 on:

- **Dip shape & cause** — how deep is the drawdown (`dist_52w_high`,
  `dist_sma200`), and is the drop driven by something *transitory* (macro/rate
  fears, a sentiment swing, sector rotation, a one-off earnings miss, a cyclical
  trough) versus a *permanent* impairment (lost moat, secular decline, a product
  AI/new tech is disrupting)?
- **Moat / AI-irreplaceability** — is the franchise durable and hard to replace,
  and crucially can **AI or a substitute technology** route around or commoditize
  its product? Favor switching costs, network effects, process-tech/patents,
  certification lock-in, brand, capital intensity; be wary of anything AI could
  disintermediate.
- **Rebound catalyst** — is there a concrete path back up (earnings recovery,
  cycle turn, new product cycle, buyback, guidance reset, margin inflection,
  cost-out, an activist, a sentiment normalization)?
- **Balance-sheet survival** — low debt, positive FCF, cash — can it comfortably
  endure the drawdown without distress or dilution?
- **Margin of safety** — has the dip made it genuinely cheap vs its own history
  and peers (forward PE, the analyst mean target upside), so downside is limited?

Keep the **top ~12-15** with the strongest *temporary-dip + intact-moat +
catalyst* narrative. Tell the user the shortlist and one-line rationale each.
Drop the rest (note why a couple of deep-discount names were dropped if they look
like value traps / permanent impairment — be honest).

---

## Phase 2 — Deep web research (parallel research subagents)

Split the ~12-15 names into 3-4 batches and spawn one **research subagent per
batch** in parallel (single message, multiple `Agent` calls). Use
`subagent_type: "claude"` with `model: "opus"`.

Give each research subagent this brief (fill in its batch of tickers):

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

Collect the returned dossiers. Assemble a single consolidated **research
dossier** (markdown) covering all ~12-15 names with their metrics + findings +
rebound scores. Save it to `output/dip/research_dossier.md`.

---

## Phase 3 — Independent nomination / ranking (Opus 4.8 voting panel)

Spawn **4 independent selection subagents** in parallel (one message, four
`Agent` calls, `subagent_type: "claude"`, `model: "opus"`). Give all four the
**same** consolidated dossier, but assign each a distinct lens so the panel
isn't an echo chamber. **In ranked top-N mode with R > 1, spawn 4×R agents
(R independent rounds of the four lenses)** — parallelize as far as is practical
(batch the messages if 4×R is large).

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

**Single-pick variant** — each subagent must return, in this exact structure:
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

**Ranked variant** — instead of one pick, each subagent **ranks its top
max(N, 10)** of the shortlisted names, best first, **through its lens** (rank a
floor of 10 even when N < 10 so the aggregate has depth below the cut line).
Require exactly this compact output so the ballots aggregate cleanly:
> A numbered list, best first: `RANK. TICKER — <=6-word reason (this lens)`.
> Then, for its **top 3 only**, 2–3 sentences on the single most compelling
> temporary-dip + intact-moat (or rebound-catalyst) data point and a rough
> 12–18mo base/bull scenario. Then one line: which names it deliberately left
> out of its top 10 and why (flag any it suspects are value traps).

---

## Phase 4A — Aggregate and pick ONE (single-pick mode)

You (the orchestrator) now decide. Do NOT just count votes mechanically:

1. Tally each agent's top pick and runner-up (weight top pick 2, runner-up 1).
2. Where agents disagree, read their reasoning and adjudicate on the merits —
   the clearest *temporary-dislocation* evidence plus a credible, dated rebound
   catalyst wins ties; a name that is cheap but whose *business* is impaired
   loses to one whose only problem is the price.
3. **Apply the value-trap filter — it can veto the vote.** A name with a
   *credible* permanent-impairment threat (AI/substitute disrupting its product,
   secular decline, an eroding moat, debt-driven survival risk) is a poor
   dip-buy even if it wins the vote — the "dip" never recovers. Treat high
   value-trap / permanent-impairment risk as a near-disqualifier; prefer the name
   whose moat is intact and whose drop is provably about sentiment, not the
   business.
4. Sanity-check the winner against the hard data in `shortlist.json` (it must
   still pass the dip doctrine — really in a dip, still profitable/growing/moaty —
   don't override the screen).
5. Choose **exactly one** final pick.

Write `output/dip/final_pick.md` with:
- **THE PICK:** ticker, company, sector/sub-industry, current market cap.
- **One-paragraph thesis** in plain language (the "why this dip rebounds").
- **Why the dip is temporary, not permanent** — the concrete, sourced evidence
  that the drop is about price/sentiment/cycle, not a broken business.
- **The dip depth** — how far below its 200-day SMA and off its 52-week high
  (`dist_sma200`, `dist_52w_high`), with the cause.
- **Why it's the category leader / why the moat is intact** — and specifically
  **why AI or a substitute cannot disrupt it** (or an honest statement of the
  disruption risk if it's the pick's main weakness).
- **The rebound catalyst & timing** — the dated trigger(s) that re-rate it.
- **Return scenario + price targets:** base vs bull case over 12-18 months, with
  the reasoning. Include an explicit **price-target table** with the current
  price, a **base-case target (price + % + by when)**, a **bull-case target
  (price + % + by when)**, and a **downside / thesis-break exit price**. Derive
  the targets from the scenario %s and anchor them to the current price and the
  analyst mean target in `shortlist.json`. Label every number a research
  scenario, not a guarantee.
- **Holding period & exit plan** — state a recommended hold horizon and *why*,
  tied to the rebound-catalyst timeline (when does the re-rating play out? what
  are the dated catalysts — next earnings, a cycle turn, a product launch, a
  buyback?). **Pair the price targets with the timing:** "base target $X by
  ~<date/quarter>; bull target $Y by ~<date> if <catalyst>; exit if it hits the
  downside trigger price $Z or any thesis-break trigger fires." Give concrete
  **thesis-break exit triggers** — observable events meaning "sell now, the dip
  was permanent after all" (the rebound catalyst slips or cancels, the moat is
  breached, AI/a substitute lands the disruptive blow, fundamentals keep
  deteriorating, the next leg down breaks the drawdown floor). Then a
  **leverage-safety note**: how the name's volatility/cyclicality should temper
  any use of leverage — a beaten-down name can keep falling and "catching a knife"
  with margin is brutal; size for the possibility the dip deepens before it turns.
  Frame this as risk education, NOT a personalized leverage recommendation — never
  suggest a specific leverage ratio or position size; surface the risks and let
  the user decide.
- **Key risks** and what would invalidate the thesis (the value-trap case).
- **The panel:** each agent's pick + conviction, and how you adjudicated.
- **Screen metrics** for the pick (pull from shortlist.json).
- A dated disclaimer: this is research output, not financial advice.

Then present a tight summary to the user: the pick, the one-line thesis, the
panel vote, and the headline return scenario. Point them to the full writeup in
`output/dip/final_pick.md`.

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
   stronger temporary-dip evidence + intact moat + a fresher dated rebound
   catalyst wins; then more #1 votes, then better average placement.
3. **Value-trap risk is a FLAG here, not a veto.** Unlike single-pick mode
   (where credible permanent-impairment near-disqualifies), in a ranking you
   **keep** such names but make the risk visible in their row — the reader sees
   the caveat and decides. Note explicitly if the strict-doctrine order at the
   top would differ from the Borda order.
4. Sanity-check every top-N name against `shortlist.json` (each must still pass
   the dip screen's doctrine — don't override the screen).
5. Produce the final ranked **top N**.

Write `output/dip/final_ranking.md` with:
- **The ranking table** — rank, ticker, company, sector/sub-industry, current
  price, analyst mean target (+upside %), forward PE, **dip depth
  (`dist_52w_high`) and rebound & irreplaceability scores**, and a one-line case
  per name. If you ran R > 1 rounds, also show **Borda points, appearances
  (e.g. 16/20), #1 votes, and average placement**.
- **Per-name thesis** — a one-paragraph thesis for at least the top 3–5 (why the
  dip is temporary, the rebound catalyst, why the moat/AI-irreplaceability holds
  OR the honest value-trap caveat); one tight line each for the rest.
- **Just-missed names** — the few that fell just outside the top N, with why.
- **What the panel revealed** — each lens's top few, where they agreed/disagreed,
  and (if R > 1) which names were conviction vs consensus, and what the averaging
  changed vs a single round.
- **If forced to ONE** — name the single pick the strict value-trap veto would
  land on, and why it may differ from the Borda #1. This keeps the doctrine
  honest even in ranked mode.
- **Return scenarios** — at minimum a base/bull headline for the top 3, anchored
  to current price and the analyst mean target in `shortlist.json`. Label every
  number a research scenario, not a guarantee.
- **Risk lens & leverage-safety note** across the list — sector concentration,
  which names are deepest in their drawdown / most likely to keep falling vs
  steadier compounders, paired with the "catching a knife with margin" reality.
  Same education-not-advice framing as single-pick mode: never a specific leverage
  multiple or position size.
- **Thesis-break / value-trap triggers** to watch across the ranked names.
- A dated disclaimer: this is research output, not financial advice.

Then present a tight summary: the ranked top-N table, the panel split (and what
multi-round averaging changed, if R > 1), and point the user to
`output/dip/final_ranking.md`.

---

## Guardrails

- **Never fabricate** financial figures, drawdown numbers, valuation multiples,
  or quotes. Attribute and date every concrete claim; if research can't confirm
  something, say so.
- **Respect the chosen mode.** Single-pick mode → **exactly one** final pick (the
  point is forcing a decision; the value-trap filter can veto the vote). Ranked
  mode → **exactly N** names (default 10), ordered, with each name's value-trap /
  permanent-impairment caveat visible rather than vetoed.
- Don't override the deterministic screen. If you think a gate is wrong, say so
  to the user, but pick (or rank) from the screened set.
- **Leverage:** you may explain how the pick's volatility/drawdown affects
  leverage *risk* (education), but never recommend a specific leverage multiple
  or position size — that's personalized advice. Always pair any leverage
  discussion with the "the dip can deepen before it turns" reality.
- This is research/education, not personalized investment advice. Always include
  the disclaimer.

# POLICY.md — position sizing & deployment policy (the human layer)

This file is the **only** place portfolio- and money-management context lives.
The picker itself stays portfolio-blind by design (see README): no script,
dossier, or panel ever reads holdings. Every number here is a default — edit it
here, once, and the skills/scorecard echo it.

The stock-pick skills must read this file and include a **sizing note** in
every writeup that echoes the formula below with the pick's own EV and bear
numbers — as the owner's pre-committed policy, not personalized advice.

---

## 1. Per-pick sizing (fractional-Kelly-lite)

Size is proportional to modeled edge per unit of modeled downside, from the
writeup's scenario table (WS-3 discipline):

```
raw      = (ev_price / price − 1) / (1 − bear_target / price)
size_pct = min(5.0, 2.5 × raw)          # % of investable capital
```

Worked example: price $231, EV $283 (+22.5%), bear $190 (−17.7%) →
raw = 0.225 / 0.177 = 1.27 → size = min(5, 3.2) = **3.2%**.

Adjustments, in order:

1. **Earnings halving** — if `next_earnings` is within **10 days** of entry,
   halve the size (event risk; the writeup must flag the date).
2. **Per-pick cap: 5%** of investable capital, always.
3. **System cap: 15%** across all open picks from this system combined
   (`scorecard.py` prints current recorded exposure vs this cap and alerts
   over it).
4. **Pilot regime (until §5 is satisfied): halve the computed size again.**

The scenario numbers feeding `raw` are AI-panel research estimates, not
measurements — treat the formula as a *discipline* that forces downside math
before money moves, and the caps as the real risk control. Never size up
because the formula "says so"; only ever size down from it.

## 2. No leverage — hard rule

Picks from this system are **cash-only**. No margin, no options as leverage
substitutes, no borrowing against the position. The dip doctrine's own warning
("catching a knife with margin is brutal") is policy here, not advice. Leverage
decisions belong to the owner's separate personal framework and never to this
repo's picks.

## 3. Deployment checklist (manual, before any order)

The system is portfolio-blind, so the overlap check is a **human step**:

- [ ] Does this pick overlap a position I already hold in size (same name,
      same niche, or tightly correlated — e.g. another AI-capex proxy)? If
      yes, reduce or skip; the ledger still records the pick either way.
- [ ] Is total open exposure from this system after this entry ≤ 15%? (Run
      `uv run python scripts/scorecard.py` — it prints the recorded total.)
- [ ] Earnings within 10 days? Halve (writeup should already flag it).
- [ ] Record the actual deployed size in the pick's ledger row (`size_pct`)
      so the scorecard can police the cap. Unfunded picks leave it empty.

## 4. The "pass" outcome is a first-class result

If the writeup's probability-weighted expected value is less than **+15%**
above the current price over 12–18 months, the run publishes as **"pass —
best of a weak field"** and appends a `kind=pass` row to the ledger instead of
an actionable pick. Deploy nothing. Passes are tracked so the scorecard can
eventually show whether they were right. The system must stay comfortable
recommending nothing.

## 5. Pilot protocol (gates scaling, not entry)

Until **both** are true, all sizes run at half (rule 1.4):

- `scorecard.py --check` has run on a schedule (cron) for a **full quarter**
  with the exit rules live, and
- the point-in-time backtest (README roadmap / WS-8) has reported whether the
  deterministic funnel alone beats SPY.

The ledger only started 2026-06-21 — the system has no realized track record
yet. Position sizes scale with evidence, not conviction.

---

*Research/educational tooling. Not financial advice.*

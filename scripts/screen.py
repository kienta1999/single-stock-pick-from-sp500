#!/usr/bin/env python3
"""Deterministic S&P 500 screen -> ~50 quality category-leaders.

Two modes share the same quality funnel but differ at the price gate (stage 5)
and the ranking score, so one script feeds both AI skills:

  --mode momentum (default) — the original doctrine (a friend's MU call:
      profitable, US, biggest in its niche, riding a structural shortage). Buys
      STRENGTH: price ABOVE its 200-day SMA; score rewards 12-month momentum.
      Consumed by the `stock-pick-momentum` skill. Writes to output/momentum/.

  --mode dip — buy a reboundable quality dip. Same quality gates, but buys
      WEAKNESS: price BELOW its 200-day SMA and off its 52-week high (but not
      wrecked — a value-trap floor drops names down more than the floor). Score
      rewards rebound headroom + quality + balance-sheet survival, not momentum.
      Consumed by the `stock-pick-dip` skill. Writes to output/dip/.

Funnel (each stage prints how many names it drops):

  0. Universe          all current S&P 500 members
  1. Profitable        TTM net income > 0
  2. US company        country == "United States"
  3. Revenue growth    TTM YoY revenue growth > 0 (also the anti-value-trap
                       gate). Uses rev_growth_ttm (smoothed, from annual
                       statements — see fetch.py) so one lumpy quarter doesn't
                       eject a compounder; falls back to Yahoo's single-quarter
                       revenueGrowth when statements are unavailable.
  4. Manageable debt   net-debt / EBITDA < MAX_NET_DEBT_EBITDA (net-cash passes)
  5. Price gate        momentum: price ABOVE its 200-day SMA
                       dip:      price BELOW its 200-day SMA, AND drawdown from
                                 the 52-week high no worse than DIP_DRAWDOWN_FLOOR
  6. Strong margins    operating margin above the company's GICS-sector median
  6b. Earnings quality dip only, soft gate (--no-eq-gate disables): drop names
                       with 2+ earnings-quality red flags (Sloan accruals,
                       cash conversion, receivables/inventory vs revenue — the
                       quantifiable value-trap signature; see fetch.py). One
                       flag never gates; every flag penalizes the composite
                       score slightly in BOTH modes and rides into
                       shortlist.json as an `earnings_quality` block.
  7. Forward profit    0 < forward P/E < MAX_FORWARD_PE — positive forward
                       earnings (makes money next year) and not an absurd
                       valuation; NaN forward P/E is dropped (conservative,
                       and the dropped tickers are printed so a missing Yahoo
                       estimate never costs a name invisibly).
                       Default ceiling tightens for dip (cheapness tilt).
  8. Niche leaders     per GICS Sub-Industry keep the top-N by market cap UNION
                       any co-leader ≥ R× the bucket's biggest name (keeps MU
                       alongside NVDA; drops small also-rans like SNDK).
                       Leadership is measured against the FULL S&P 500 universe,
                       not the gate survivors — so a #4 name can't become a
                       "leader" just because the real leaders failed a gate.
  9. Trim to target    if >TARGET remain, rank by a mode-specific composite
                       quality/explosive (momentum) or rebound (dip) score and
                       keep the top TARGET

Outputs (under output/<mode>/):
    shortlist.csv    human-readable, ranked
    shortlist.json   full records for the stock-pick skill to consume
    funnel.json      the stage-by-stage drop counts (audit trail)

Run scripts/fetch.py first (it populates the caches this reads).

CLI:
    python scripts/screen.py                       # momentum (default)
    python scripts/screen.py --mode dip            # buy-the-dip screen
    python scripts/screen.py --mode dip --dip-drawdown-floor 0.40
    python scripts/screen.py --target 50 --max-net-debt-ebitda 3.0
    python scripts/screen.py --no-trim             # keep all category leaders
"""

import argparse
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from fetch import load_metrics  # noqa: E402

_ROOT = os.path.dirname(_HERE)
# Per-mode output folder: output/momentum/ or output/dip/. Resolved via
# _output_dir(mode); the three filenames inside are identical across modes.
OUTPUT_ROOT = os.path.join(_ROOT, "output")
MODES = ("momentum", "dip")


def _output_dir(mode: str) -> str:
    return os.path.join(OUTPUT_ROOT, mode)


DEFAULT_TARGET = 50
DEFAULT_MAX_NET_DEBT_EBITDA = 3.0
# Forward-valuation gate (stage 7). A high cap, not a value screen: it's a
# sanity backstop. 0 < forwardPE enforces positive forward earnings ("makes
# money next year"); the < 60 ceiling sits well above the legitimate growth
# range (the universe tops out ~50) so it only ever catches absurd blow-off
# names, never a real franchise like HWM (~46) or the semi-equipment complex.
DEFAULT_MAX_FORWARD_PE = 60.0
# Dip mode tightens the ceiling — a reboundable quality dip should also be a
# margin-of-safety entry, not a still-expensive falling knife.
DEFAULT_MAX_FORWARD_PE_DIP = 35.0
# Dip price gate (stage 5). Keep names BELOW their 200-day SMA but drop the
# falling knives: anything more than this fraction below its 52-week high is
# usually a broken thesis, not a reboundable correction.
DEFAULT_DIP_DRAWDOWN_FLOOR = 0.55
US_COUNTRY = "United States"

# Category-leader stage (7). GICS sub-industries are coarse — "Semiconductors"
# holds NVDA, AVGO, MU, AMD together — so a single #1-per-bucket rule throws away
# genuine niche leaders. We keep the union of two rules: the top-N by market cap,
# AND any "co-leader" whose market cap is at least COLEADER_RATIO of its
# sub-industry's biggest name (proportional, so it scales across sectors and
# keeps a giant like MU while still dropping small also-rans like SNDK).
DEFAULT_LEADERS_PER_SUBINDUSTRY = 2
DEFAULT_COLEADER_RATIO = 0.20


# ─────────────────────────────────────────────────────────────────────────────
# Derived metrics
# ─────────────────────────────────────────────────────────────────────────────


def _add_derived(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Net debt and leverage. net_debt < 0 == net cash (a good thing).
    df["net_debt"] = df["totalDebt"].fillna(0) - df["totalCash"].fillna(0)
    df["net_debt_ebitda"] = np.where(
        (df["ebitda"].notna()) & (df["ebitda"] > 0),
        df["net_debt"] / df["ebitda"],
        np.nan,
    )
    # Leverage as used by the composite score: a net-cash company with no
    # usable EBITDA has the best possible balance sheet, not a neutral one —
    # rank it best instead of letting NaN fall to the 0.5 neutral fill.
    df["net_debt_ebitda_rankable"] = np.where(
        (df["net_debt"] <= 0) & df["net_debt_ebitda"].isna(),
        -np.inf,
        df["net_debt_ebitda"],
    )
    # Growth as used by gate + score: smoothed TTM YoY when statements gave us
    # one, else Yahoo's single-quarter YoY.
    ttm = df["rev_growth_ttm"] if "rev_growth_ttm" in df.columns else pd.Series(np.nan, index=df.index)
    df["rev_growth"] = ttm.fillna(df["revenueGrowth"])
    # Analyst implied upside (sanity signal, not a gate).
    df["analyst_upside"] = np.where(
        (df["targetMeanPrice"].notna()) & (df["price"].notna()) & (df["price"] > 0),
        df["targetMeanPrice"] / df["price"] - 1,
        np.nan,
    )
    # Niche leadership, measured against the FULL universe (everything fetched),
    # before any gate: a name's sub-industry rank and its size relative to the
    # sub-industry's biggest member must not depend on which peers happen to
    # survive the funnel (e.g. in dip mode the true leader is usually NOT in a
    # dip — the #4 name must not inherit "leader" status by default).
    g = df.groupby("gics_sub_industry")["marketCap"]
    df["subind_rank"] = g.rank(method="first", ascending=False)
    df["mc_vs_subind_leader"] = df["marketCap"] / g.transform("max")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Gate helpers
# ─────────────────────────────────────────────────────────────────────────────


def _leverage_ok(row: pd.Series, cap: float) -> bool:
    # Net cash is always fine.
    if pd.notna(row["net_debt"]) and row["net_debt"] <= 0:
        return True
    nde = row["net_debt_ebitda"]
    if pd.isna(nde):
        return False  # have positive net debt but no usable EBITDA -> conservative drop
    return nde < cap


def _rank_pct(s: pd.Series, ascending: bool = True) -> pd.Series:
    """Cross-sectional percentile rank in [0,1]; NaN -> 0.5 (neutral)."""
    r = s.rank(ascending=ascending, pct=True)
    return r.fillna(0.5)


# Composite weight tables (documented in README — keep in sync). Each metric
# maps to (weight, ascending) for _rank_pct; weights per mode MUST sum to 1.0
# (asserted below).
#   momentum: growth and 12-month momentum first, then quality, then valuation
#             headroom — the explosive-compounder thesis.
#   dip:      rebound headroom (analyst upside) and drawdown depth first, then
#             quality and balance-sheet survival — the reboundable-dip thesis.
#             Deliberately does NOT reward momentum (beaten down by construction).
COMPOSITE_WEIGHTS = {
    "momentum": {
        "rev_growth": (0.30, True),
        "ret_12m": (0.20, True),
        "operatingMargins": (0.15, True),
        "returnOnEquity": (0.15, True),
        "analyst_upside": (0.10, True),
        "net_debt_ebitda_rankable": (0.10, False),  # less leverage better
    },
    "dip": {
        "analyst_upside": (0.25, True),             # headroom to mean target
        "dist_52w_high": (0.20, False),             # more beaten-down = more room
        "operatingMargins": (0.15, True),           # quality intact
        "returnOnEquity": (0.15, True),             # quality intact
        "rev_growth": (0.15, True),                 # still growing (not a trap)
        "net_debt_ebitda_rankable": (0.10, False),  # survival: less leverage better
    },
}
# Earnings-quality penalty on the composite (both modes): percentile points off
# per red flag, capped. A penalty, not a weight — flags are sparse and the
# composite must stay a 0-1 percentile blend for the un-flagged majority.
EQ_PENALTY_PER_FLAG = 0.03
EQ_PENALTY_CAP = 0.06


def _n_eq_flags(df: pd.DataFrame) -> pd.Series:
    """Red-flag count per row, for the 6b gate and the composite penalty.
    Financials are exempt (count 0): banks/insurers structurally 'fail'
    CFO/NI and receivables-vs-revenue (their receivables are loans, their
    cashflow isn't working-capital-driven) — the working-capital framework
    doesn't apply. Their metrics still ride into shortlist.json so the
    research brief can interrogate them."""
    if "eq_flags" not in df.columns:
        return pd.Series(0, index=df.index)
    n = df["eq_flags"].fillna("").map(lambda s: len([f for f in str(s).split(",") if f]))
    return n.where(df["gics_sector"] != "Financials", 0)


def _composite_score(df: pd.DataFrame, mode: str = "momentum") -> pd.Series:
    """Rank-based blend (scale-robust, NaN-tolerant) minus the earnings-quality
    penalty. Higher = more attractive. Used only to trim/rank, never to gate."""
    weights = COMPOSITE_WEIGHTS[mode]
    total = sum(w for w, _ in weights.values())
    assert abs(total - 1.0) < 1e-9, f"{mode} composite weights sum to {total}, not 1.0"
    score = sum(w * _rank_pct(df[col], ascending=asc)
                for col, (w, asc) in weights.items())
    penalty = (_n_eq_flags(df) * EQ_PENALTY_PER_FLAG).clip(upper=EQ_PENALTY_CAP)
    return score - penalty


# ─────────────────────────────────────────────────────────────────────────────
# The funnel
# ─────────────────────────────────────────────────────────────────────────────


def run_screen(
    target: int = DEFAULT_TARGET,
    max_net_debt_ebitda: float = DEFAULT_MAX_NET_DEBT_EBITDA,
    max_forward_pe: float = DEFAULT_MAX_FORWARD_PE,
    leaders_per_subindustry: int = DEFAULT_LEADERS_PER_SUBINDUSTRY,
    coleader_ratio: float = DEFAULT_COLEADER_RATIO,
    trim: bool = True,
    mode: str = "momentum",
    dip_drawdown_floor: float = DEFAULT_DIP_DRAWDOWN_FLOOR,
    eq_gate: bool = True,
) -> tuple[pd.DataFrame, list[dict]]:
    df = load_metrics()
    if df.empty:
        raise SystemExit("No metrics found. Run `python scripts/fetch.py` first.")
    df = _add_derived(df)

    funnel: list[dict] = []

    def stage(name: str, mask: pd.Series, frame: pd.DataFrame) -> pd.DataFrame:
        kept = frame[mask].copy()
        funnel.append({"stage": name, "in": len(frame), "out": len(kept), "dropped": len(frame) - len(kept)})
        print(f"  {name:<22} {len(frame):>4} -> {len(kept):>4}  (dropped {len(frame) - len(kept)})", flush=True)
        return kept

    print(f"\nFunnel (start: {len(df)} S&P 500 members with data):", flush=True)

    # 1. Profitable — TTM net income > 0 (fall back to profit margin sign).
    profitable = df["netIncomeToCommon"].fillna(
        df["profitMargins"].apply(lambda m: 1.0 if pd.notna(m) and m > 0 else (-1.0 if pd.notna(m) else np.nan))
    ) > 0
    df = stage("1 profitable", profitable, df)

    # 2. US company.
    df = stage("2 US company", df["country"] == US_COUNTRY, df)

    # 3. Revenue growth YoY > 0, on the smoothed TTM measure (rev_growth falls
    #    back to Yahoo's single-quarter revenueGrowth where statements are
    #    missing — see _add_derived).
    n_fallback = int((df["rev_growth_ttm"].isna() & df["revenueGrowth"].notna()).sum()) \
        if "rev_growth_ttm" in df.columns else len(df)
    if n_fallback:
        print(f"  (growth gate: {n_fallback} names lack TTM statements, using quarterly YoY fallback)", flush=True)
    df = stage("3 TTM rev growth>0", df["rev_growth"].fillna(-1) > 0, df)

    # 4. Manageable leverage.
    df = stage("4 leverage ok", df.apply(lambda r: _leverage_ok(r, max_net_debt_ebitda), axis=1), df)

    # 5. Price gate. momentum buys strength (above 200d SMA); dip buys weakness
    #    (below 200d SMA) but drops falling knives via a drawdown floor.
    if mode == "dip":
        df = stage("5 below 200d SMA", (df["dist_sma200"] < 0).fillna(False), df)
        within_floor = df["dist_52w_high"] >= -dip_drawdown_floor
        df = stage(f"5b drawdown >=-{dip_drawdown_floor:g}", within_floor.fillna(False), df)
    else:
        df = stage("5 above 200d SMA", df["above_sma200"].fillna(False), df)

    # 6. Operating margin above the company's GICS-sector median (computed over
    #    the survivors of 1-5 so the benchmark is profitable, growing US peers).
    sector_median = df.groupby("gics_sector")["operatingMargins"].transform("median")
    strong_margin = df["operatingMargins"] > sector_median
    df = stage("6 op margin>sector med", strong_margin.fillna(False), df)

    # 6b. Earnings quality (dip mode only, soft gate): a name triggering 2+ of
    #     the red flags (high accruals / low cash conversion / receivables or
    #     inventory outrunning revenue — see fetch.py) is the quantitative
    #     signature of the value trap the dip doctrine hunts. ONE flag never
    #     gates (business-model context needed — that's the research brief's
    #     job); flags always feed the composite penalty in both modes.
    #     Disable with --no-eq-gate.
    if mode == "dip" and eq_gate:
        n_flags = _n_eq_flags(df)
        for _, r in df[n_flags >= 2].iterrows():
            print(f"  (eq gate: dropping {r['ticker']} — flags: {r['eq_flags']})", flush=True)
        df = stage("6b earnings quality", n_flags < 2, df)

    # 7. Forward profitability + valuation sanity. 0 < forwardPE enforces
    #    positive forward earnings ("makes money next year"); the high ceiling is
    #    a backstop against absurd valuations, not a value screen — it sits well
    #    above the legit growth range so it never bites a real franchise. NaN
    #    forward P/E (no estimate) is dropped, consistent with the leverage gate
    #    — but those tickers are named, so a missing Yahoo estimate never costs
    #    a candidate invisibly.
    fwd = df["forwardPE"]
    no_estimate = sorted(df.loc[fwd.isna(), "ticker"])
    if no_estimate:
        print(f"  (fwdPE gate: dropping {len(no_estimate)} with NO forward-PE estimate: "
              f"{', '.join(no_estimate)})", flush=True)
    forward_ok = (fwd > 0) & (fwd < max_forward_pe)
    df = stage(f"7 0<fwdPE<{max_forward_pe:g}", forward_ok.fillna(False), df)

    # 8. Category leader — keep the niche's genuine leaders, drop the also-rans.
    #    GICS sub-industries are coarse (NVDA, AVGO, MU, AMD all = "Semiconductors")
    #    so a single #1-per-bucket rule discards real franchises like MU's memory
    #    business. Keep the UNION of:
    #      (a) top-N by market cap in the sub-industry (the clear leaders), and
    #      (b) any "co-leader" whose market cap ≥ coleader_ratio × the bucket's
    #          biggest name (proportional → keeps a giant like MU at 25% of NVDA,
    #          drops small tag-alongs like SNDK; "between MU and SNDK, pick MU").
    #    subind_rank / mc_vs_subind_leader come from _add_derived and are
    #    measured against the FULL universe, not the survivors — otherwise (esp.
    #    in dip mode, where the true leader is usually not dipping) a #4 name
    #    would inherit "leader" status just because its betters failed a gate.
    keep = (df["subind_rank"] <= leaders_per_subindustry) | (df["mc_vs_subind_leader"] >= coleader_ratio)
    label = f"8 niche leaders (N={leaders_per_subindustry},R={coleader_ratio:g})"
    df = stage(label, keep.fillna(False), df)
    funnel[-1].update({
        "leaders_per_subindustry": leaders_per_subindustry,
        "coleader_ratio": coleader_ratio,
    })

    # 9. Composite score + optional trim to target.
    df["composite_score"] = _composite_score(df, mode=mode)
    df = df.sort_values("composite_score", ascending=False).reset_index(drop=True)
    n_in = len(df)
    if trim and len(df) > target:
        df = df.head(target).copy()
        funnel.append({"stage": "9 trim to target", "in": n_in, "out": len(df),
                       "dropped": n_in - len(df), "target": target})
        print(f"  {'9 trim to target':<22} {n_in:>4} -> {len(df):>4}  (top {target} by composite score)", flush=True)
    else:
        funnel.append({"stage": "9 trim to target", "in": n_in, "out": len(df),
                       "dropped": 0, "target": target, "trimmed": False})

    df.insert(0, "rank", range(1, len(df) + 1))
    return df, funnel


# ─────────────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────────────

# Columns surfaced in the human-readable CSV (full record goes to JSON).
# dist_52w_high is the dip-depth signal — useful in momentum CSVs too, central
# to the dip screen.
CSV_COLS = [
    "rank", "ticker", "security", "gics_sector", "gics_sub_industry",
    "marketCap", "composite_score",
    "rev_growth_ttm", "revenueGrowth", "operatingMargins", "profitMargins", "returnOnEquity",
    "net_debt_ebitda", "dist_sma200", "dist_52w_high", "ret_12m", "analyst_upside",
    "trailingPE", "forwardPE", "recommendationKey",
    "accrual_ratio", "cfo_ni", "eq_flags",
]

_DOCTRINE = {
    "momentum": "profitable + US + TTM-revenue-growth + manageable-leverage + "
                "positive-momentum (price ABOVE 200d SMA) + strong-margins + "
                "positive-forward-earnings (0<fwdPE<cap), then category leaders "
                "per GICS sub-industry (leadership measured vs the full "
                "universe), trimmed by composite quality/explosive "
                "(growth + momentum) score.",
    "dip": "profitable + US + TTM-revenue-growth (anti-value-trap) + "
           "manageable-leverage + IN A DIP (price BELOW 200d SMA, drawdown from "
           "52w high within floor) + strong-margins + positive-forward-earnings "
           "(0<fwdPE<cap, tighter for cheapness), then category leaders per GICS "
           "sub-industry (leadership measured vs the full universe), trimmed by "
           "composite rebound score (analyst upside + drawdown room + quality + "
           "balance-sheet survival).",
}


def _write_outputs(df: pd.DataFrame, funnel: list[dict], mode: str = "momentum") -> None:
    output_dir = _output_dir(mode)
    os.makedirs(output_dir, exist_ok=True)

    csv_cols = [c for c in CSV_COLS if c in df.columns]
    csv_path = os.path.join(output_dir, "shortlist.csv")
    df[csv_cols].to_csv(csv_path, index=False)

    json_path = os.path.join(output_dir, "shortlist.json")
    records = json.loads(df.replace({np.nan: None}).to_json(orient="records"))
    # Nest the flat earnings-quality fields into one block per record; a
    # missing metric stays an explicit null with the reason in `note`.
    from fetch import EQ_FIELDS
    for rec in records:
        flags = rec.pop("eq_flags", None) or ""
        rec["earnings_quality"] = {
            **{k: rec.pop(k, None) for k in EQ_FIELDS},
            "flags": [f for f in flags.split(",") if f],
            "note": rec.pop("eq_note", None),
        }
    payload = {
        "generated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "count": len(df),
        "doctrine": _DOCTRINE.get(mode, _DOCTRINE["momentum"]),
        "candidates": records,
    }
    with open(json_path, "w") as f:
        json.dump(payload, f, indent=2)

    with open(os.path.join(output_dir, "funnel.json"), "w") as f:
        json.dump(funnel, f, indent=2)

    print(f"\nWrote {len(df)} candidates ({mode} mode) to:")
    print(f"  {csv_path}")
    print(f"  {json_path}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mode", choices=MODES, default="momentum",
                    help="momentum (default): buy strength, price ABOVE 200d SMA, "
                         "writes output/momentum/. dip: buy a reboundable quality "
                         "dip, price BELOW 200d SMA within the drawdown floor, "
                         "writes output/dip/.")
    ap.add_argument("--target", type=int, default=DEFAULT_TARGET, help="Shortlist size to trim to.")
    ap.add_argument("--max-net-debt-ebitda", type=float, default=DEFAULT_MAX_NET_DEBT_EBITDA)
    ap.add_argument("--max-forward-pe", type=float, default=None,
                    help="Forward-P/E ceiling. Names must have 0 < forwardPE < this "
                         "— positive forward earnings and not an absurd valuation. "
                         "Defaults to 60 (momentum) / 35 (dip, cheapness tilt) when "
                         "not given.")
    ap.add_argument("--dip-drawdown-floor", type=float, default=DEFAULT_DIP_DRAWDOWN_FLOOR,
                    help="Dip mode only: drop names down more than this fraction "
                         "from their 52-week high (default 0.55 → keeps corrections, "
                         "rejects falling knives).")
    ap.add_argument("--leaders-per-subindustry", type=int, default=DEFAULT_LEADERS_PER_SUBINDUSTRY,
                    help="Keep at least the top-N market-cap names per GICS "
                         "sub-industry (default 2).")
    ap.add_argument("--coleader-ratio", type=float, default=DEFAULT_COLEADER_RATIO,
                    help="Also keep any name whose market cap is ≥ this fraction "
                         "of its sub-industry leader (default 0.20 → keeps MU at "
                         "~25%% of NVDA, drops small also-rans). Set to 1.0 to "
                         "disable and rely on top-N alone.")
    ap.add_argument("--no-trim", action="store_true", help="Keep all category leaders (skip the stage-9 trim).")
    ap.add_argument("--no-eq-gate", action="store_true",
                    help="Dip mode only: disable the stage-6b earnings-quality "
                         "soft gate (2+ red flags drops a name). Flags still "
                         "penalize the composite and appear in the shortlist.")
    args = ap.parse_args()

    max_forward_pe = args.max_forward_pe
    if max_forward_pe is None:
        max_forward_pe = DEFAULT_MAX_FORWARD_PE_DIP if args.mode == "dip" else DEFAULT_MAX_FORWARD_PE

    df, funnel = run_screen(
        target=args.target,
        max_net_debt_ebitda=args.max_net_debt_ebitda,
        max_forward_pe=max_forward_pe,
        leaders_per_subindustry=args.leaders_per_subindustry,
        coleader_ratio=args.coleader_ratio,
        trim=not args.no_trim,
        mode=args.mode,
        dip_drawdown_floor=args.dip_drawdown_floor,
        eq_gate=not args.no_eq_gate,
    )
    _write_outputs(df, funnel, mode=args.mode)

    print(f"\nTop 15 by composite score ({args.mode} mode):")
    perf_col = "dist_52w_high" if args.mode == "dip" else "ret_12m"
    show = ["rank", "ticker", "security", "gics_sub_industry", "marketCap",
            "rev_growth", "operatingMargins", perf_col, "analyst_upside", "composite_score"]
    show = [c for c in show if c in df.columns]
    with pd.option_context("display.max_rows", None, "display.width", 200,
                           "display.float_format", lambda x: f"{x:,.3f}"):
        print(df[show].head(15).to_string(index=False))


if __name__ == "__main__":
    main()

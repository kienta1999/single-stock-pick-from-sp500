#!/usr/bin/env python3
"""Deterministic S&P 500 screen -> ~50 quality category-leaders.

Encodes the investment doctrine (a friend's MU call: profitable, US, the
biggest in its niche, riding a structural shortage) as a hard, repeatable
funnel. The output shortlist is what the AI `stock-pick` skill then researches
and votes on.

Funnel (each stage prints how many names it drops):

  0. Universe          all current S&P 500 members
  1. Profitable        TTM net income > 0
  2. US company        country == "United States"
  3. Revenue growth    YoY revenue growth > 0
  4. Manageable debt   net-debt / EBITDA < MAX_NET_DEBT_EBITDA (net-cash passes)
  5. Positive momentum price above its 200-day SMA
  6. Strong margins    operating margin above the company's GICS-sector median
  7. Niche leaders     per GICS Sub-Industry keep the top-N by market cap UNION
                       any co-leader ≥ R× the bucket's biggest name (keeps MU
                       alongside NVDA; drops small also-rans like SNDK)
  8. Trim to target    if >TARGET remain, rank by a composite quality/explosive
                       score and keep the top TARGET

Outputs:
    output/shortlist.csv    human-readable, ranked
    output/shortlist.json   full records for the stock-pick skill to consume
    output/funnel.json      the stage-by-stage drop counts (audit trail)

Run scripts/fetch.py first (it populates the caches this reads).

CLI:
    python scripts/screen.py
    python scripts/screen.py --target 50 --max-net-debt-ebitda 3.0
    python scripts/screen.py --no-trim          # keep all category leaders
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
OUTPUT_DIR = os.path.join(_ROOT, "output")

DEFAULT_TARGET = 50
DEFAULT_MAX_NET_DEBT_EBITDA = 3.0
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
    # Analyst implied upside (sanity signal, not a gate).
    df["analyst_upside"] = np.where(
        (df["targetMeanPrice"].notna()) & (df["price"].notna()) & (df["price"] > 0),
        df["targetMeanPrice"] / df["price"] - 1,
        np.nan,
    )
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


def _composite_score(df: pd.DataFrame) -> pd.Series:
    """Quality + explosiveness blend. Higher = more attractive. Rank-based so
    it's scale-robust and NaN-tolerant. Tuned toward the thesis: reward growth
    and momentum first, then quality, then valuation headroom."""
    score = (
        0.30 * _rank_pct(df["revenueGrowth"])
        + 0.20 * _rank_pct(df["ret_12m"])
        + 0.15 * _rank_pct(df["operatingMargins"])
        + 0.15 * _rank_pct(df["returnOnEquity"])
        + 0.10 * _rank_pct(df["analyst_upside"])
        + 0.10 * _rank_pct(df["net_debt_ebitda"], ascending=False)  # less leverage better
    )
    return score


# ─────────────────────────────────────────────────────────────────────────────
# The funnel
# ─────────────────────────────────────────────────────────────────────────────


def run_screen(
    target: int = DEFAULT_TARGET,
    max_net_debt_ebitda: float = DEFAULT_MAX_NET_DEBT_EBITDA,
    leaders_per_subindustry: int = DEFAULT_LEADERS_PER_SUBINDUSTRY,
    coleader_ratio: float = DEFAULT_COLEADER_RATIO,
    trim: bool = True,
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

    # 3. Revenue growth YoY > 0.
    df = stage("3 revenue growth>0", df["revenueGrowth"].fillna(-1) > 0, df)

    # 4. Manageable leverage.
    df = stage("4 leverage ok", df.apply(lambda r: _leverage_ok(r, max_net_debt_ebitda), axis=1), df)

    # 5. Positive momentum — above 200d SMA.
    df = stage("5 above 200d SMA", df["above_sma200"].fillna(False), df)

    # 6. Operating margin above the company's GICS-sector median (computed over
    #    the survivors of 1-5 so the benchmark is profitable, growing US peers).
    sector_median = df.groupby("gics_sector")["operatingMargins"].transform("median")
    strong_margin = df["operatingMargins"] > sector_median
    df = stage("6 op margin>sector med", strong_margin.fillna(False), df)

    # 7. Category leader — keep the niche's genuine leaders, drop the also-rans.
    #    GICS sub-industries are coarse (NVDA, AVGO, MU, AMD all = "Semiconductors")
    #    so a single #1-per-bucket rule discards real franchises like MU's memory
    #    business. Keep the UNION of:
    #      (a) top-N by market cap in the sub-industry (the clear leaders), and
    #      (b) any "co-leader" whose market cap ≥ coleader_ratio × the bucket's
    #          biggest name (proportional → keeps a giant like MU at 25% of NVDA,
    #          drops small tag-alongs like SNDK; "between MU and SNDK, pick MU").
    df = df.sort_values("marketCap", ascending=False)
    g = df.groupby("gics_sub_industry", sort=False)
    subind_rank = g["marketCap"].rank(method="first", ascending=False)
    leader_mc = g["marketCap"].transform("max")
    mc_vs_leader = df["marketCap"] / leader_mc
    keep = (subind_rank <= leaders_per_subindustry) | (mc_vs_leader >= coleader_ratio)
    df = df[keep].copy()
    label = f"7 niche leaders (N={leaders_per_subindustry},R={coleader_ratio:g})"
    funnel.append({
        "stage": label, "out": len(df),
        "leaders_per_subindustry": leaders_per_subindustry,
        "coleader_ratio": coleader_ratio,
    })
    print(f"  {label:<28} -> {len(df):>4}  (top-{leaders_per_subindustry} ∪ ≥{coleader_ratio:g}× leader per sub-industry)", flush=True)

    # 8. Composite score + optional trim to target.
    df["composite_score"] = _composite_score(df)
    df = df.sort_values("composite_score", ascending=False).reset_index(drop=True)
    if trim and len(df) > target:
        df = df.head(target).copy()
        funnel.append({"stage": "8 trim to target", "out": len(df), "target": target})
        print(f"  {'8 trim to target':<22} -> {len(df):>4}  (top {target} by composite score)", flush=True)
    else:
        funnel.append({"stage": "8 trim to target", "out": len(df), "target": target, "trimmed": False})

    df.insert(0, "rank", range(1, len(df) + 1))
    return df, funnel


# ─────────────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────────────

# Columns surfaced in the human-readable CSV (full record goes to JSON).
CSV_COLS = [
    "rank", "ticker", "security", "gics_sector", "gics_sub_industry",
    "marketCap", "composite_score",
    "revenueGrowth", "operatingMargins", "profitMargins", "returnOnEquity",
    "net_debt_ebitda", "dist_sma200", "ret_12m", "analyst_upside",
    "trailingPE", "forwardPE", "recommendationKey",
]


def _write_outputs(df: pd.DataFrame, funnel: list[dict]) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    csv_cols = [c for c in CSV_COLS if c in df.columns]
    csv_path = os.path.join(OUTPUT_DIR, "shortlist.csv")
    df[csv_cols].to_csv(csv_path, index=False)

    json_path = os.path.join(OUTPUT_DIR, "shortlist.json")
    records = json.loads(df.replace({np.nan: None}).to_json(orient="records"))
    payload = {
        "generated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(df),
        "doctrine": "profitable + US + revenue-growth + manageable-leverage + "
                    "positive-momentum + strong-margins, then #1 market cap per "
                    "GICS sub-industry, trimmed by composite quality/explosive score.",
        "candidates": records,
    }
    with open(json_path, "w") as f:
        json.dump(payload, f, indent=2)

    with open(os.path.join(OUTPUT_DIR, "funnel.json"), "w") as f:
        json.dump(funnel, f, indent=2)

    print(f"\nWrote {len(df)} candidates to:")
    print(f"  {csv_path}")
    print(f"  {json_path}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--target", type=int, default=DEFAULT_TARGET, help="Shortlist size to trim to.")
    ap.add_argument("--max-net-debt-ebitda", type=float, default=DEFAULT_MAX_NET_DEBT_EBITDA)
    ap.add_argument("--leaders-per-subindustry", type=int, default=DEFAULT_LEADERS_PER_SUBINDUSTRY,
                    help="Keep at least the top-N market-cap names per GICS "
                         "sub-industry (default 2).")
    ap.add_argument("--coleader-ratio", type=float, default=DEFAULT_COLEADER_RATIO,
                    help="Also keep any name whose market cap is ≥ this fraction "
                         "of its sub-industry leader (default 0.20 → keeps MU at "
                         "~25%% of NVDA, drops small also-rans). Set to 1.0 to "
                         "disable and rely on top-N alone.")
    ap.add_argument("--no-trim", action="store_true", help="Keep all category leaders (skip stage 8 trim).")
    args = ap.parse_args()

    df, funnel = run_screen(
        target=args.target,
        max_net_debt_ebitda=args.max_net_debt_ebitda,
        leaders_per_subindustry=args.leaders_per_subindustry,
        coleader_ratio=args.coleader_ratio,
        trim=not args.no_trim,
    )
    _write_outputs(df, funnel)

    print("\nTop 15 by composite score:")
    show = ["rank", "ticker", "security", "gics_sub_industry", "marketCap",
            "revenueGrowth", "operatingMargins", "ret_12m", "composite_score"]
    show = [c for c in show if c in df.columns]
    with pd.option_context("display.max_rows", None, "display.width", 200,
                           "display.float_format", lambda x: f"{x:,.3f}"):
        print(df[show].head(15).to_string(index=False))


if __name__ == "__main__":
    main()

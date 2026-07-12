#!/usr/bin/env python3
"""Fetch + cache the raw data the screen needs, one row of truth per ticker.

Three sources, all yfinance (kept deliberately lean — this is a current-snapshot
screen, not the full point-in-time XBRL pipeline of ml-stock-forward-return):

  1. Prices       -> data/prices/{TICKER}.parquet   (~13 months of daily OHLCV)
                     Drives momentum: distance from 200d SMA, 52w-high, 6/12m return.
  2. Info         -> data/info/{TICKER}.json        (yfinance Ticker.get_info())
                     Drives fundamentals: market cap, margins, revenue growth,
                     leverage, country, sector/industry names.
  3. Fundamentals -> data/fundamentals/{TICKER}.json (annual income statement)
                     Annual revenue series, used to compute rev_growth_ttm — a
                     smoothed trailing-twelve-month YoY revenue growth (see
                     load_metrics) so the screen's growth gate doesn't hinge on
                     a single quarter's comp.
  4. Quarterly    -> data/quarterly/{TICKER}.json (quarterly IS/CF/BS series)
                     Drives the earnings-quality red flags (value-trap
                     detector): Sloan accrual ratio, cash-conversion (CFO/NI),
                     and receivables/inventory-vs-revenue divergence. Falls
                     back to annual statements when quarterly is sparse.

Both caches are age-gated (re-fetched when older than *_MAX_AGE_DAYS) so repeat
runs in the same week are instant. `--refresh` forces a full re-fetch.

Public loader (used by screen.py):
    load_metrics(tickers) -> DataFrame, one row per ticker, with every raw
    field the funnel filters on. Tickers with no usable data are dropped.

CLI:
    python scripts/fetch.py                      # full S&P 500 universe
    python scripts/fetch.py --tickers MU,NVDA    # subset (debugging)
    python scripts/fetch.py --refresh            # ignore caches
    python scripts/fetch.py --workers 12
"""

import argparse
import json
import os
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
from tqdm import tqdm

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from universe import get_tickers  # noqa: E402

_ROOT = os.path.dirname(_HERE)
PRICES_DIR = os.path.join(_ROOT, "data", "prices")
INFO_DIR = os.path.join(_ROOT, "data", "info")
FUND_DIR = os.path.join(_ROOT, "data", "fundamentals")
QUART_DIR = os.path.join(_ROOT, "data", "quarterly")

PRICE_PERIOD = "13mo"        # enough for 200d SMA + 252d (12m) lookback with buffer
PRICE_MAX_AGE_DAYS = 1
INFO_MAX_AGE_DAYS = 3
FUND_MAX_AGE_DAYS = 7        # annual statements change quarterly at most
QUART_MAX_AGE_DAYS = 7

# Earnings-quality red-flag thresholds (value-trap detector; flags, not gates —
# except dip mode's soft 2-flag gate in screen.py). Sourced from the
# working-capital methodology in the improvement plan.
EQ_ACCRUAL_RED = 0.05        # Sloan accruals (NI-CFO)/avg assets above +5%
EQ_CFO_NI_RED = 0.60         # cash conversion CFO/NI below 0.6
EQ_RECV_DIV_RED = 0.10       # receivables YoY outrunning revenue YoY by >10pp
EQ_INV_DIV_RED = 0.15        # inventory YoY outrunning revenue YoY by >15pp
EQ_INV_MIN_SHARE = 0.05      # inventory divergence only judged when inv > 5% of revenue
EQ_FIELDS = ["accrual_ratio", "cfo_ni", "recv_rev_divergence", "inv_rev_divergence"]
RETRIES = 3
RETRY_SLEEP = 1.5
WORKERS = 8

# yfinance info keys we keep. Everything the funnel and the downstream AI skill
# might want, nothing else (info dicts are huge and noisy).
INFO_KEYS = [
    "longName", "country", "sector", "industry",
    "marketCap", "enterpriseValue", "sharesOutstanding",
    "trailingPE", "forwardPE", "priceToBook",
    "profitMargins", "operatingMargins", "grossMargins", "ebitdaMargins",
    "revenueGrowth", "earningsGrowth", "revenuePerShare",
    "totalRevenue", "ebitda", "netIncomeToCommon",
    "totalDebt", "totalCash", "debtToEquity",
    "returnOnEquity", "returnOnAssets", "freeCashflow",
    "currentPrice", "targetMeanPrice", "recommendationKey",
    "fullTimeEmployees",
]


# ─────────────────────────────────────────────────────────────────────────────
# Prices
# ─────────────────────────────────────────────────────────────────────────────


def _price_path(ticker: str) -> str:
    return os.path.join(PRICES_DIR, f"{ticker}.parquet")


def _price_cache_fresh(ticker: str) -> bool:
    p = _price_path(ticker)
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        return False
    return (time.time() - os.path.getmtime(p)) / 86400 < PRICE_MAX_AGE_DAYS


def _download_prices(ticker: str) -> pd.DataFrame | None:
    for attempt in range(1, RETRIES + 1):
        try:
            df = yf.download(
                ticker, period=PRICE_PERIOD, auto_adjust=True,
                progress=False, threads=False,
            )
            if df is None or df.empty:
                # Yahoo signals rate-limiting by returning empty rather than
                # raising — retry instead of giving up.
                if attempt == RETRIES:
                    return None
                time.sleep(RETRY_SLEEP * attempt)
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df.index.name = "Date"
            return df[df["Close"].notna()]
        except Exception as e:
            if attempt == RETRIES:
                print(f"  [{ticker}] price download failed: {e}", flush=True)
                return None
            time.sleep(RETRY_SLEEP * attempt)
    return None


def fetch_price(ticker: str, refresh: bool = False) -> bool:
    if not refresh and _price_cache_fresh(ticker):
        return True
    df = _download_prices(ticker)
    if df is None or df.empty:
        return False
    df.to_parquet(_price_path(ticker))
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Info (fundamentals snapshot)
# ─────────────────────────────────────────────────────────────────────────────


def _info_path(ticker: str) -> str:
    return os.path.join(INFO_DIR, f"{ticker}.json")


def _info_cache_fresh(ticker: str) -> bool:
    p = _info_path(ticker)
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        return False
    return (time.time() - os.path.getmtime(p)) / 86400 < INFO_MAX_AGE_DAYS


def _download_info(ticker: str) -> dict | None:
    for attempt in range(1, RETRIES + 1):
        try:
            raw = yf.Ticker(ticker).get_info()
            if not raw:
                return None
            slim = {k: raw.get(k) for k in INFO_KEYS}
            slim["_fetched"] = time.strftime("%Y-%m-%d %H:%M:%S")
            return slim
        except Exception as e:
            if attempt == RETRIES:
                print(f"  [{ticker}] info fetch failed: {e}", flush=True)
                return None
            time.sleep(RETRY_SLEEP * attempt)
    return None


def fetch_info(ticker: str, refresh: bool = False) -> bool:
    if not refresh and _info_cache_fresh(ticker):
        return True
    info = _download_info(ticker)
    if info is None:
        return False
    with open(_info_path(ticker), "w") as f:
        json.dump(info, f)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Fundamentals (annual revenue series, for TTM revenue growth)
# ─────────────────────────────────────────────────────────────────────────────


def _fund_path(ticker: str) -> str:
    return os.path.join(FUND_DIR, f"{ticker}.json")


def _fund_cache_fresh(ticker: str) -> bool:
    p = _fund_path(ticker)
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        return False
    return (time.time() - os.path.getmtime(p)) / 86400 < FUND_MAX_AGE_DAYS


def _download_fund(ticker: str) -> dict | None:
    """Annual Total Revenue per fiscal-year end date, newest first."""
    for attempt in range(1, RETRIES + 1):
        try:
            stmt = yf.Ticker(ticker).income_stmt
            if stmt is None or stmt.empty or "Total Revenue" not in stmt.index:
                if attempt == RETRIES:
                    return None
                time.sleep(RETRY_SLEEP * attempt)
                continue
            rev = stmt.loc["Total Revenue"].dropna()
            annual = {d.strftime("%Y-%m-%d"): float(v) for d, v in rev.items()}
            return {
                "annual_revenue": dict(sorted(annual.items(), reverse=True)),
                "_fetched": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            if attempt == RETRIES:
                print(f"  [{ticker}] fundamentals fetch failed: {e}", flush=True)
                return None
            time.sleep(RETRY_SLEEP * attempt)
    return None


def fetch_fund(ticker: str, refresh: bool = False) -> bool:
    if not refresh and _fund_cache_fresh(ticker):
        return True
    fund = _download_fund(ticker)
    if fund is None:
        return False
    with open(_fund_path(ticker), "w") as f:
        json.dump(fund, f)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Quarterly statements (earnings-quality red flags)
# ─────────────────────────────────────────────────────────────────────────────


def _quart_path(ticker: str) -> str:
    return os.path.join(QUART_DIR, f"{ticker}.json")


def _quart_cache_fresh(ticker: str) -> bool:
    p = _quart_path(ticker)
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        return False
    return (time.time() - os.path.getmtime(p)) / 86400 < QUART_MAX_AGE_DAYS


def _stmt_series(stmt: pd.DataFrame | None, labels: list[str]) -> dict:
    """First matching row label -> {date: value}, newest first. {} if absent."""
    if stmt is None or stmt.empty:
        return {}
    for label in labels:
        if label in stmt.index:
            s = stmt.loc[label].dropna()
            if not s.empty:
                return dict(sorted(((d.strftime("%Y-%m-%d"), float(v)) for d, v in s.items()),
                                   reverse=True))
    return {}


def _download_quarterly(ticker: str) -> dict | None:
    """Quarterly NI / revenue / CFO / total assets / receivables / inventory
    series (newest first). When the quarterly CFO or assets history is too
    sparse for a TTM window, the annual cashflow/balance-sheet series are
    fetched too so the metrics can fall back."""
    for attempt in range(1, RETRIES + 1):
        try:
            tk = yf.Ticker(ticker)
            out = {
                "q_ni": _stmt_series(tk.quarterly_income_stmt, ["Net Income"]),
                "q_rev": _stmt_series(tk.quarterly_income_stmt, ["Total Revenue"]),
                "q_cfo": _stmt_series(tk.quarterly_cashflow,
                                      ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"]),
                "q_assets": _stmt_series(tk.quarterly_balance_sheet, ["Total Assets"]),
                "q_recv": _stmt_series(tk.quarterly_balance_sheet,
                                       ["Accounts Receivable", "Receivables", "Net Receivables"]),
                "q_inv": _stmt_series(tk.quarterly_balance_sheet, ["Inventory"]),
            }
            if len(out["q_cfo"]) < 4 or len(out["q_ni"]) < 4:
                out["a_ni"] = _stmt_series(tk.income_stmt, ["Net Income"])
                out["a_cfo"] = _stmt_series(tk.cashflow,
                                            ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
            if len(out["q_assets"]) < 2:
                out["a_assets"] = _stmt_series(tk.balance_sheet, ["Total Assets"])
            if not any(out.values()):
                if attempt == RETRIES:
                    return None
                time.sleep(RETRY_SLEEP * attempt)
                continue
            out["_fetched"] = time.strftime("%Y-%m-%d %H:%M:%S")
            return out
        except Exception as e:
            if attempt == RETRIES:
                print(f"  [{ticker}] quarterly fetch failed: {e}", flush=True)
                return None
            time.sleep(RETRY_SLEEP * attempt)
    return None


def fetch_quarterly(ticker: str, refresh: bool = False) -> bool:
    if not refresh and _quart_cache_fresh(ticker):
        return True
    q = _download_quarterly(ticker)
    if q is None:
        return False
    with open(_quart_path(ticker), "w") as f:
        json.dump(q, f)
    return True


def _eq_metrics(ni_ttm, cfo_ttm, avg_assets, recv_yoy=None, rev_yoy=None,
                inv_yoy=None, inv_share=None) -> dict:
    """Pure earnings-quality math -> the four metrics + red flags. Any input
    None -> that metric is None and cannot flag (null-safety doctrine)."""
    out: dict = {k: None for k in EQ_FIELDS}
    flags: list[str] = []

    if ni_ttm is not None and cfo_ttm is not None and avg_assets:
        out["accrual_ratio"] = (ni_ttm - cfo_ttm) / avg_assets
        if out["accrual_ratio"] > EQ_ACCRUAL_RED:
            flags.append("HIGH_ACCRUALS")
    if ni_ttm is not None and cfo_ttm is not None and ni_ttm > 0:
        out["cfo_ni"] = cfo_ttm / ni_ttm
        if out["cfo_ni"] < EQ_CFO_NI_RED:
            flags.append("LOW_CASH_CONVERSION")
    if recv_yoy is not None and rev_yoy is not None:
        out["recv_rev_divergence"] = recv_yoy - rev_yoy
        if out["recv_rev_divergence"] > EQ_RECV_DIV_RED:
            flags.append("RECEIVABLES_OUTRUN")
    # Inventory divergence is only meaningful for inventory-heavy models.
    if (inv_yoy is not None and rev_yoy is not None
            and inv_share is not None and inv_share > EQ_INV_MIN_SHARE):
        out["inv_rev_divergence"] = inv_yoy - rev_yoy
        if out["inv_rev_divergence"] > EQ_INV_DIV_RED:
            flags.append("INVENTORY_BUILD")

    out["eq_flags"] = ",".join(flags)
    return out


def _ttm_sum(series: dict) -> float | None:
    vals = list(series.values())
    return sum(vals[:4]) if len(vals) >= 4 else None


def _yoy(series: dict) -> float | None:
    """Latest point vs the point 4 quarters back; positive base required."""
    vals = list(series.values())
    if len(vals) >= 5 and vals[4] and vals[4] > 0:
        return vals[0] / vals[4] - 1
    return None


def eq_from_cache(ticker: str) -> dict:
    """Assemble the earnings-quality inputs for one ticker from the quarterly
    cache (annual fallbacks when sparse) and run _eq_metrics. Always returns
    all EQ_FIELDS + eq_flags + eq_note (the why, when data was missing)."""
    empty = {k: None for k in EQ_FIELDS} | {"eq_flags": "", "eq_note": None}
    p = _quart_path(ticker)
    if not os.path.exists(p):
        return empty | {"eq_note": "no quarterly statements cached"}
    try:
        with open(p) as f:
            q = json.load(f)
    except Exception:
        return empty | {"eq_note": "quarterly cache unreadable"}

    notes: list[str] = []
    ni, cfo = _ttm_sum(q.get("q_ni", {})), _ttm_sum(q.get("q_cfo", {}))
    if ni is None or cfo is None:
        a_ni = list(q.get("a_ni", {}).values())
        a_cfo = list(q.get("a_cfo", {}).values())
        if a_ni and a_cfo:
            ni, cfo = a_ni[0], a_cfo[0]
            notes.append("NI/CFO from latest annual (quarterly sparse)")
        else:
            ni = cfo = None
            notes.append("NI/CFO unavailable")

    assets = list(q.get("q_assets", {}).values())
    if len(assets) >= 2:
        avg_assets = (assets[0] + assets[min(4, len(assets) - 1)]) / 2
    else:
        a_assets = list(q.get("a_assets", {}).values())
        avg_assets = (sum(a_assets[:2]) / 2) if len(a_assets) >= 2 else (
            a_assets[0] if a_assets else None)
        if avg_assets is not None:
            notes.append("assets from annual")
        else:
            notes.append("assets unavailable")
    if avg_assets is not None and avg_assets <= 0:
        avg_assets = None

    rev_yoy = _yoy(q.get("q_rev", {}))
    recv_yoy = _yoy(q.get("q_recv", {}))
    inv_yoy = _yoy(q.get("q_inv", {}))
    ttm_rev = _ttm_sum(q.get("q_rev", {}))
    inv_vals = list(q.get("q_inv", {}).values())
    inv_share = (inv_vals[0] / ttm_rev) if inv_vals and ttm_rev else None

    out = _eq_metrics(ni, cfo, avg_assets, recv_yoy=recv_yoy, rev_yoy=rev_yoy,
                      inv_yoy=inv_yoy, inv_share=inv_share)
    out["eq_note"] = "; ".join(notes) if notes else None
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Universe fetch (parallel)
# ─────────────────────────────────────────────────────────────────────────────


def fetch_universe(tickers: list[str], refresh: bool = False, workers: int = WORKERS) -> None:
    os.makedirs(PRICES_DIR, exist_ok=True)
    os.makedirs(INFO_DIR, exist_ok=True)
    os.makedirs(FUND_DIR, exist_ok=True)
    os.makedirs(QUART_DIR, exist_ok=True)

    def _one(t: str) -> tuple[str, bool, bool, bool, bool]:
        return (t, fetch_price(t, refresh), fetch_info(t, refresh),
                fetch_fund(t, refresh), fetch_quarterly(t, refresh))

    ok_price = ok_info = ok_fund = ok_quart = 0
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, t): t for t in tickers}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="Fetch"):
            t, p, i, fu, qu = fut.result()
            ok_price += p
            ok_info += i
            ok_fund += fu
            ok_quart += qu
            if not (p and i):  # statements are optional (gates fall back / flag null)
                failed.append(t)

    print(f"\nDone. prices ok={ok_price}/{len(tickers)}  info ok={ok_info}/{len(tickers)}"
          f"  fundamentals ok={ok_fund}/{len(tickers)}  quarterly ok={ok_quart}/{len(tickers)}", flush=True)
    if failed:
        print(f"{len(failed)} tickers missing price and/or info: {', '.join(sorted(failed))}", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Metric assembly (price-derived momentum + info fundamentals)
# ─────────────────────────────────────────────────────────────────────────────


def _momentum_from_prices(df: pd.DataFrame) -> dict:
    """Trend/momentum metrics from one ticker's OHLCV. NaN where insufficient history."""
    c = df["Close"]
    last = float(c.iloc[-1])
    out: dict = {"price": last}

    sma200 = c.rolling(200).mean().iloc[-1]
    out["dist_sma200"] = last / sma200 - 1 if pd.notna(sma200) and sma200 > 0 else np.nan
    out["above_sma200"] = bool(out["dist_sma200"] > 0) if pd.notna(out["dist_sma200"]) else False

    window = c.iloc[-252:] if len(c) >= 252 else c
    high_52w = window.max()
    out["dist_52w_high"] = last / high_52w - 1 if high_52w > 0 else np.nan

    def _ret(n: int) -> float:
        if len(c) > n:
            past = float(c.iloc[-(n + 1)])
            return last / past - 1 if past > 0 else np.nan
        return np.nan

    out["ret_6m"] = _ret(126)
    out["ret_12m"] = _ret(252)
    return out


def _rev_growth_ttm(ttm_revenue, annual_revenue: dict) -> float:
    """Smoothed TTM YoY revenue growth: current TTM revenue vs the TTM one year
    earlier. Yahoo's `totalRevenue` is already trailing-twelve-month; the prior
    year's TTM isn't directly available (Yahoo returns only ~5 quarters), so
    interpolate it from the last two fiscal-year totals: with fraction f of a
    year elapsed since the latest fiscal-year end, prior TTM ≈ A1 + f*(A0 - A1)
    — exact at a fiscal-year boundary, smooth in between. Far less noisy than
    the single-quarter YoY in Yahoo's `revenueGrowth`."""
    if not ttm_revenue or ttm_revenue <= 0 or not annual_revenue:
        return np.nan
    fy_ends = sorted(annual_revenue, reverse=True)
    if len(fy_ends) < 2:
        return np.nan
    a0, a1 = annual_revenue[fy_ends[0]], annual_revenue[fy_ends[1]]
    if not a1 or a1 <= 0 or not a0 or a0 <= 0:
        return np.nan
    f = (pd.Timestamp.now() - pd.Timestamp(fy_ends[0])).days / 365.25
    f = min(max(f, 0.0), 1.0)
    prior_ttm = a1 + f * (a0 - a1)
    return float(ttm_revenue) / prior_ttm - 1


def load_metrics(tickers: list[str] | None = None) -> pd.DataFrame:
    """One row per ticker: GICS tags + momentum + fundamentals. Cached data only
    (run fetch_universe first). Tickers missing both price and info are dropped
    (and reported, so silent data loss is visible)."""
    from universe import get_universe

    uni = get_universe()
    if tickers is not None:
        uni = uni[uni["Ticker"].isin(tickers)]

    rows: list[dict] = []
    no_data: list[str] = []
    for _, u in uni.iterrows():
        t = u["Ticker"]
        row: dict = {
            "ticker": t,
            "security": u.get("Security"),
            "gics_sector": u.get("GICS Sector"),
            "gics_sub_industry": u.get("GICS Sub-Industry"),
        }

        # Info
        ip = _info_path(t)
        if os.path.exists(ip):
            try:
                with open(ip) as f:
                    info = json.load(f)
                for k in INFO_KEYS:
                    row[k] = info.get(k)
            except Exception:
                pass

        # Momentum from prices
        pp = _price_path(t)
        if os.path.exists(pp):
            try:
                pdf = pd.read_parquet(pp)
                if not pdf.empty:
                    row.update(_momentum_from_prices(pdf))
            except Exception:
                pass

        # Smoothed TTM revenue growth (NaN when statements unavailable — the
        # screen falls back to the quarterly `revenueGrowth`).
        row["rev_growth_ttm"] = np.nan
        fp = _fund_path(t)
        if os.path.exists(fp):
            try:
                with open(fp) as f:
                    fund = json.load(f)
                row["rev_growth_ttm"] = _rev_growth_ttm(
                    row.get("totalRevenue"), fund.get("annual_revenue") or {})
            except Exception:
                pass

        # Earnings-quality red flags (null-safe: missing statements -> None
        # metrics + a note, never a silent gate).
        row.update(eq_from_cache(t))

        # Keep only rows with at least a market cap (the minimum the funnel needs).
        if row.get("marketCap"):
            rows.append(row)
        else:
            no_data.append(t)

    if no_data:
        print(f"NOTE: {len(no_data)} universe tickers had no usable cached data "
              f"and are excluded: {', '.join(sorted(no_data))}", flush=True)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("marketCap", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tickers", help="Comma-separated subset (default: full S&P 500).")
    ap.add_argument("--refresh", action="store_true", help="Ignore caches, re-fetch all.")
    ap.add_argument("--workers", type=int, default=WORKERS)
    args = ap.parse_args()

    if args.tickers:
        tickers = [t.strip().upper().replace(".", "-") for t in args.tickers.split(",") if t.strip()]
    else:
        tickers = get_tickers()

    print(f"Fetching {len(tickers)} tickers (workers={args.workers}, refresh={args.refresh})...", flush=True)
    fetch_universe(tickers, refresh=args.refresh, workers=args.workers)


if __name__ == "__main__":
    main()

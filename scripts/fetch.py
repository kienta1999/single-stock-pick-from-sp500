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

PRICE_PERIOD = "13mo"        # enough for 200d SMA + 252d (12m) lookback with buffer
PRICE_MAX_AGE_DAYS = 1
INFO_MAX_AGE_DAYS = 3
FUND_MAX_AGE_DAYS = 7        # annual statements change quarterly at most
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
# Universe fetch (parallel)
# ─────────────────────────────────────────────────────────────────────────────


def fetch_universe(tickers: list[str], refresh: bool = False, workers: int = WORKERS) -> None:
    os.makedirs(PRICES_DIR, exist_ok=True)
    os.makedirs(INFO_DIR, exist_ok=True)
    os.makedirs(FUND_DIR, exist_ok=True)

    def _one(t: str) -> tuple[str, bool, bool, bool]:
        return t, fetch_price(t, refresh), fetch_info(t, refresh), fetch_fund(t, refresh)

    ok_price = ok_info = ok_fund = 0
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, t): t for t in tickers}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="Fetch"):
            t, p, i, fu = fut.result()
            ok_price += p
            ok_info += i
            ok_fund += fu
            if not (p and i):  # fundamentals are optional (growth gate falls back)
                failed.append(t)

    print(f"\nDone. prices ok={ok_price}/{len(tickers)}  info ok={ok_info}/{len(tickers)}"
          f"  fundamentals ok={ok_fund}/{len(tickers)}", flush=True)
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

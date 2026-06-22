#!/usr/bin/env python3
"""Fetch + cache the raw data the screen needs, one row of truth per ticker.

Two sources, both yfinance (kept deliberately lean — this is a current-snapshot
screen, not the full point-in-time XBRL pipeline of ml-stock-forward-return):

  1. Prices   -> data/prices/{TICKER}.parquet   (~13 months of daily OHLCV)
                 Drives momentum: distance from 200d SMA, 52w-high, 6/12m return.
  2. Info     -> data/info/{TICKER}.json        (yfinance Ticker.get_info())
                 Drives fundamentals: market cap, margins, revenue growth,
                 leverage, country, sector/industry names.

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

PRICE_PERIOD = "13mo"        # enough for 200d SMA + 252d (12m) lookback with buffer
PRICE_MAX_AGE_DAYS = 1
INFO_MAX_AGE_DAYS = 3
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
                return None
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
# Universe fetch (parallel)
# ─────────────────────────────────────────────────────────────────────────────


def fetch_universe(tickers: list[str], refresh: bool = False, workers: int = WORKERS) -> None:
    os.makedirs(PRICES_DIR, exist_ok=True)
    os.makedirs(INFO_DIR, exist_ok=True)

    def _one(t: str) -> tuple[str, bool, bool]:
        return t, fetch_price(t, refresh), fetch_info(t, refresh)

    ok_price = ok_info = 0
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, t): t for t in tickers}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="Fetch"):
            t, p, i = fut.result()
            ok_price += p
            ok_info += i
            if not (p and i):
                failed.append(t)

    print(f"\nDone. prices ok={ok_price}/{len(tickers)}  info ok={ok_info}/{len(tickers)}", flush=True)
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


def load_metrics(tickers: list[str] | None = None) -> pd.DataFrame:
    """One row per ticker: GICS tags + momentum + fundamentals. Cached data only
    (run fetch_universe first). Tickers missing both price and info are dropped."""
    from universe import get_universe

    uni = get_universe()
    if tickers is not None:
        uni = uni[uni["Ticker"].isin(tickers)]

    rows: list[dict] = []
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

        # Keep only rows with at least a market cap (the minimum the funnel needs).
        if row.get("marketCap"):
            rows.append(row)

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

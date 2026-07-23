#!/usr/bin/env python3
"""Current S&P 500 roster with GICS classification.

This is a *live snapshot* screener (not a point-in-time backtest), so unlike
the sibling ranker-21d-sp500 project we don't need the historical
membership CSV — only today's members and their GICS Sector / Sub-Industry,
both of which come from the Wikipedia roster in a single scrape.

The GICS Sub-Industry tag is load-bearing here: it's how we encode the
"biggest in what it's doing" rule (keep the #1 market-cap name per
sub-industry) downstream in screen.py.

Cache:
    data/universe/sp500_roster.csv   Ticker, Security, GICS Sector, GICS Sub-Industry, as_of

Public API:
    get_universe(force_refresh=False) -> DataFrame
    get_tickers(force_refresh=False)  -> list[str]

CLI:
    python scripts/universe.py            # build/refresh if stale
    python scripts/universe.py --refresh  # force re-scrape
"""

import io
import os
import sys
import time
import warnings
from datetime import datetime, timezone

warnings.filterwarnings("ignore")

import pandas as pd
import requests

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UDIR = os.path.join(_ROOT, "data", "universe")
ROSTER_FILE = os.path.join(_UDIR, "sp500_roster.csv")

ROSTER_MAX_AGE_DAYS = 7
WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def _normalize_ticker(t: str) -> str:
    # yfinance uses '-' for class shares (BRK.B -> BRK-B).
    return str(t).strip().replace(".", "-").upper()


def _cache_is_fresh() -> bool:
    if not os.path.exists(ROSTER_FILE):
        return False
    age_days = (time.time() - os.path.getmtime(ROSTER_FILE)) / 86400
    return age_days < ROSTER_MAX_AGE_DAYS


def _fetch_roster_from_wikipedia() -> pd.DataFrame:
    print("Fetching S&P 500 roster from Wikipedia...", flush=True)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; sp500-stock-picker/1.0)"}
    html = requests.get(WIKIPEDIA_URL, headers=headers, timeout=20).text
    df = pd.read_html(io.StringIO(html))[0]
    keep = ["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]
    df = df[keep].rename(columns={"Symbol": "Ticker"})
    df["Ticker"] = df["Ticker"].map(_normalize_ticker)
    df = df.drop_duplicates(subset=["Ticker"]).reset_index(drop=True)
    df["as_of"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return df


def get_universe(force_refresh: bool = False) -> pd.DataFrame:
    """Current S&P 500 members with GICS Sector / Sub-Industry tags."""
    os.makedirs(_UDIR, exist_ok=True)
    if not force_refresh and _cache_is_fresh():
        return pd.read_csv(ROSTER_FILE)
    df = _fetch_roster_from_wikipedia()
    df.to_csv(ROSTER_FILE, index=False)
    print(f"Roster cached to {ROSTER_FILE} ({len(df)} tickers).", flush=True)
    return df


def get_tickers(force_refresh: bool = False) -> list[str]:
    return get_universe(force_refresh=force_refresh)["Ticker"].tolist()


def main() -> None:
    force = "--refresh" in sys.argv
    df = get_universe(force_refresh=force)
    print(f"\n{len(df)} S&P 500 members (as of {df['as_of'].iloc[0]}).")
    print("\nGICS Sector breakdown:")
    print(df["GICS Sector"].value_counts().to_string())
    print(f"\n{df['GICS Sub-Industry'].nunique()} distinct GICS Sub-Industries.")


if __name__ == "__main__":
    main()

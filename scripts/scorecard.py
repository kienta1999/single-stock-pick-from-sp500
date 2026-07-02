#!/usr/bin/env python3
"""Score every recorded pick against reality (and against SPY).

Reads picks/ledger.csv — the append-only record the stock-pick skills write
after each run (see .claude/skills/shared/pick-protocol.md for the schema) —
fetches current prices, and reports per pick:

    return since pick date, SPY's return over the same window, the alpha,
    and progress toward the writeup's base target (when one was recorded).

This is the feedback loop the picker itself lacks: without it there's no way
to know whether the doctrine beats buying the index.

CLI:
    python scripts/scorecard.py            # score everything in the ledger
    python scripts/scorecard.py --mode dip # one strategy only
"""

import argparse
import os
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from fetch import PRICE_MAX_AGE_DAYS, _price_cache_fresh, _price_path  # noqa: E402

_ROOT = os.path.dirname(_HERE)
LEDGER = os.path.join(_ROOT, "picks", "ledger.csv")


def _closes(ticker: str, period: str = "13mo") -> pd.Series | None:
    """Daily closes, newest last. Uses fetch.py's parquet cache when fresh."""
    if _price_cache_fresh(ticker):
        try:
            return pd.read_parquet(_price_path(ticker))["Close"]
        except Exception:
            pass
    try:
        df = yf.download(ticker, period=period, auto_adjust=True,
                         progress=False, threads=False)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df["Close"].dropna()
    except Exception:
        return None


def _ret_since(closes: pd.Series, since: pd.Timestamp) -> float:
    """Return from the last close on/before `since` to the latest close."""
    past = closes[closes.index <= since]
    if past.empty:
        return np.nan
    return float(closes.iloc[-1]) / float(past.iloc[-1]) - 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mode", choices=["momentum", "dip"], help="Score one strategy only.")
    args = ap.parse_args()

    if not os.path.exists(LEDGER):
        raise SystemExit(f"No ledger at {LEDGER} — run a stock-pick skill first.")
    led = pd.read_csv(LEDGER)
    if args.mode:
        led = led[led["mode"] == args.mode]
    if led.empty:
        raise SystemExit("Nothing to score.")
    led["date"] = pd.to_datetime(led["date"])

    spy = _closes("SPY")
    if spy is None:
        raise SystemExit("Could not fetch SPY for the benchmark.")

    print(f"Scoring {len(led)} ledger rows as of {spy.index[-1].date()} "
          f"(cache: prices <{PRICE_MAX_AGE_DAYS}d old are reused)...\n", flush=True)

    rows = []
    for _, r in led.iterrows():
        closes = _closes(r["ticker"])
        now = float(closes.iloc[-1]) if closes is not None and len(closes) else np.nan
        ret = now / r["price_at_pick"] - 1 if pd.notna(now) else np.nan
        spy_ret = _ret_since(spy, r["date"])
        base = r.get("base_target")
        to_base = (base / now - 1) if pd.notna(base) and pd.notna(now) and now > 0 else np.nan
        rows.append({
            "date": r["date"].date(), "mode": r["mode"], "kind": r["kind"],
            "rank": r["rank"], "ticker": r["ticker"],
            "entry": r["price_at_pick"], "now": now,
            "ret": ret, "spy": spy_ret, "alpha": ret - spy_ret,
            "base_tgt": base, "to_base": to_base,
        })

    out = pd.DataFrame(rows)
    disp = out.copy()  # pre-format to strings: float-column na_rep would override formatters
    for c, f in [("entry", "{:,.2f}"), ("now", "{:,.2f}"), ("ret", "{:+.1%}"),
                 ("spy", "{:+.1%}"), ("alpha", "{:+.1%}"),
                 ("base_tgt", "{:,.0f}"), ("to_base", "{:+.1%}")]:
        disp[c] = out[c].map(lambda x, f=f: f.format(x) if pd.notna(x) else "")
    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(disp.to_string(index=False))

    print("\nPer strategy/run (equal-weight mean):")
    grp = out.groupby(["mode", "kind", "date"]).agg(
        n=("ticker", "size"), ret=("ret", "mean"),
        spy=("spy", "mean"), alpha=("alpha", "mean"))
    for (mode, kind, date), g in grp.iterrows():
        print(f"  {date} {mode:<8} {kind:<7} n={int(g['n']):>2}  "
              f"ret {g['ret']:+.1%}  spy {g['spy']:+.1%}  alpha {g['alpha']:+.1%}")

    print("\nScenario targets and returns are research bookkeeping, not financial advice.")


if __name__ == "__main__":
    main()

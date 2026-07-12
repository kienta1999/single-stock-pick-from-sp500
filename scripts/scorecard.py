#!/usr/bin/env python3
"""Score every recorded pick against reality (and against SPY) — with exit rules.

Reads picks/ledger.csv — the append-only record the stock-pick skills write
after each run (see .claude/skills/shared/pick-protocol.md for the schema) —
fetches current prices, and classifies every row through the exit-rules engine:

    AT_TARGET  the high since the pick reached the base target -> reassess:
               take profit or re-underwrite with a NEW ledger row, never
               silently ride.
    STOPPED    a close since the pick breached the stop. The stop is the
               recorded bear_target (that's the point of writing one down),
               falling back to the legacy exit_price column, falling back to
               entry x (1 - --stop-pct, default 25%).
    EXPIRED    today is past base_by plus the grace window (--grace-days,
               default 90) — wrong about timing even if the price is flat.
    OPEN       none of the above; reports unrealized return, SPY alpha, and
               progress to the base target.
    TRACKED    no base_target recorded (ranked names below the top 3) — priced
               and benchmarked, but not rule-evaluated.
    CLOSED     a kind=close row references this pick; it feeds the realized
               track record instead.
    PASS       a kind=pass row (the run concluded "buy nothing") — kept so the
               scorecard can eventually show whether passes were right.

Closing a pick = appending a kind=close row (same date+mode+ticker as the
original, exit_price = realized fill, exit_date, exit_reason) — the ledger
stays append-only. Realized rows produce the track-record table: realized
return, SPY alpha over the holding window, hit rate, average win/loss, per
mode. That table is the number that eventually answers "does the doctrine
beat SPY".

CLI:
    python scripts/scorecard.py              # score everything in the ledger
    python scripts/scorecard.py --mode dip   # one strategy only
    python scripts/scorecard.py --check      # exit non-zero + ALERTS section
                                             # when any exit rule fires (cron)
    python scripts/scorecard.py --ledger path/to/fixture.csv
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

DEFAULT_STOP_PCT = 0.25     # stop fallback when no bear_target/exit_price recorded
DEFAULT_GRACE_DAYS = 90     # thesis-expiry grace past base_by
MAX_TOTAL_EXPOSURE_PCT = 15.0  # POLICY.md: cap across all open picks from this system

# Statuses that demand action (the --check alert set).
ALERT_STATUSES = ("AT_TARGET", "STOPPED", "EXPIRED")


def _px(ticker: str, period: str = "13mo") -> pd.DataFrame | None:
    """Daily Close+High, newest last. Uses fetch.py's parquet cache when fresh."""
    if _price_cache_fresh(ticker):
        try:
            return pd.read_parquet(_price_path(ticker))[["Close", "High"]]
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
        return df[["Close", "High"]].dropna(subset=["Close"])
    except Exception:
        return None


def _ret_between(closes: pd.Series, since: pd.Timestamp,
                 until: pd.Timestamp | None = None) -> float:
    """Return from the last close on/before `since` to the last close on/before
    `until` (latest close when until is None)."""
    past = closes[closes.index <= since]
    if past.empty:
        return np.nan
    end = closes if until is None else closes[closes.index <= until]
    if end.empty:
        return np.nan
    return float(end.iloc[-1]) / float(past.iloc[-1]) - 1


def _parse_by(val) -> pd.Timestamp | None:
    """End-of-period date for a base_by/bear_by cell: YYYY-Qn, YYYY-Hn,
    YYYY-MM, or YYYY. None when empty/unparseable."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip().upper()
    if not s:
        return None
    q_ends = {"Q1": "03-31", "Q2": "06-30", "Q3": "09-30", "Q4": "12-31",
              "H1": "06-30", "H2": "12-31"}
    try:
        if "-" in s:
            year, rest = s.split("-", 1)
            if rest in q_ends:
                return pd.Timestamp(f"{year}-{q_ends[rest]}")
            # YYYY-MM -> end of that month
            return pd.Timestamp(f"{s}-01") + pd.offsets.MonthEnd(0)
        return pd.Timestamp(f"{s}-12-31")
    except Exception:
        return None


def _first_hit(frame: pd.DataFrame, since: pd.Timestamp, col: str,
               level: float, direction: str) -> pd.Timestamp | None:
    """First date after `since` where frame[col] crossed `level` (up|down)."""
    w = frame[frame.index > since]
    hit = w[w[col] >= level] if direction == "up" else w[w[col] <= level]
    return hit.index[0] if not hit.empty else None


def _classify(r: pd.Series, px: pd.DataFrame | None, today: pd.Timestamp,
              stop_pct: float, grace_days: int) -> tuple[str, str]:
    """Exit-rules engine for one open pick row -> (status, detail)."""
    if pd.isna(r.get("base_target")):
        return "TRACKED", ""
    if px is None or px.empty:
        return "OPEN", "no price data"

    entry = r["price_at_pick"]
    stop = r.get("bear_target")
    stop_src = "bear_target"
    if pd.isna(stop):
        stop, stop_src = r.get("exit_price"), "exit_price"
    if pd.isna(stop):
        stop, stop_src = entry * (1 - stop_pct), f"entry-{stop_pct:.0%}"

    # Rule 1+2 evaluated chronologically: whichever level was crossed FIRST
    # since the pick decides — a stop that fired before the later recovery
    # to target is still a stop.
    t_hit = _first_hit(px, r["date"], "High", float(r["base_target"]), "up")
    s_hit = _first_hit(px, r["date"], "Close", float(stop), "down")
    if t_hit is not None and (s_hit is None or t_hit <= s_hit):
        return "AT_TARGET", f"high>=base {r['base_target']:g} on {t_hit.date()}"
    if s_hit is not None:
        return "STOPPED", f"close<=stop {float(stop):g} ({stop_src}) on {s_hit.date()}"

    # Rule 3: thesis expiry.
    by = _parse_by(r.get("base_by"))
    if by is not None and today > by + pd.Timedelta(days=grace_days):
        return "EXPIRED", f"past base_by {r['base_by']} +{grace_days}d grace"
    return "OPEN", ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mode", choices=["momentum", "dip"], help="Score one strategy only.")
    ap.add_argument("--ledger", default=LEDGER, help="Alternate ledger CSV (fixtures/tests).")
    ap.add_argument("--check", action="store_true",
                    help="Alert mode: print ALERTS and exit non-zero when any exit rule fires.")
    ap.add_argument("--stop-pct", type=float, default=DEFAULT_STOP_PCT,
                    help="Stop fallback when no bear_target/exit_price is recorded (default 0.25).")
    ap.add_argument("--grace-days", type=int, default=DEFAULT_GRACE_DAYS,
                    help="Grace past base_by before EXPIRED (default 90).")
    args = ap.parse_args()

    if not os.path.exists(args.ledger):
        raise SystemExit(f"No ledger at {args.ledger} — run a stock-pick skill first.")
    led = pd.read_csv(args.ledger)
    if args.mode:
        led = led[led["mode"] == args.mode]
    if led.empty:
        raise SystemExit("Nothing to score.")
    led["date"] = pd.to_datetime(led["date"])

    closes_rows = led[led["kind"] == "close"]
    picks = led[~led["kind"].isin(["close", "pass"])].copy()
    passes = led[led["kind"] == "pass"]
    closed_keys = {(c["date"], c["mode"], c["ticker"]) for _, c in closes_rows.iterrows()}

    spy_px = _px("SPY")
    if spy_px is None:
        raise SystemExit("Could not fetch SPY for the benchmark.")
    spy = spy_px["Close"]
    today = spy.index[-1]

    print(f"Scoring {len(picks)} pick rows as of {today.date()} "
          f"(cache: prices <{PRICE_MAX_AGE_DAYS}d old are reused)...\n", flush=True)

    rows = []
    alerts: list[str] = []
    for _, r in picks.iterrows():
        px = _px(r["ticker"])
        now = float(px["Close"].iloc[-1]) if px is not None and len(px) else np.nan
        ret = now / r["price_at_pick"] - 1 if pd.notna(now) else np.nan
        spy_ret = _ret_between(spy, r["date"])
        base = r.get("base_target")
        to_base = (base / now - 1) if pd.notna(base) and pd.notna(now) and now > 0 else np.nan

        if (r["date"], r["mode"], r["ticker"]) in closed_keys:
            status, detail = "CLOSED", "see realized table"
        else:
            status, detail = _classify(r, px, today, args.stop_pct, args.grace_days)
        if status in ALERT_STATUSES:
            alerts.append(f"{status:<9} {r['ticker']:<6} {r['mode']}/{r['kind']} "
                          f"picked {r['date'].date()} @ {r['price_at_pick']:g} — {detail}")

        rows.append({
            "date": r["date"].date(), "mode": r["mode"], "kind": r["kind"],
            "rank": r["rank"], "ticker": r["ticker"],
            "entry": r["price_at_pick"], "now": now,
            "ret": ret, "spy": spy_ret, "alpha": ret - spy_ret,
            "base_tgt": base, "to_base": to_base, "status": status,
        })

    out = pd.DataFrame(rows)
    disp = out.copy()  # pre-format to strings: float-column na_rep would override formatters
    for c, f in [("entry", "{:,.2f}"), ("now", "{:,.2f}"), ("ret", "{:+.1%}"),
                 ("spy", "{:+.1%}"), ("alpha", "{:+.1%}"),
                 ("base_tgt", "{:,.0f}"), ("to_base", "{:+.1%}")]:
        disp[c] = out[c].map(lambda x, f=f: f.format(x) if pd.notna(x) else "")
    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(disp.to_string(index=False))

    # ── Realized track record (kind=close rows matched to their originals) ──
    if not closes_rows.empty:
        realized = []
        for _, c in closes_rows.iterrows():
            orig = picks[(picks["date"] == c["date"]) & (picks["mode"] == c["mode"])
                         & (picks["ticker"] == c["ticker"])]
            if orig.empty or pd.isna(c.get("exit_price")):
                print(f"\nWARNING: close row {c['ticker']} {c['date'].date()} "
                      f"has no matching pick or no exit_price — skipped.")
                continue
            o = orig.iloc[0]
            exit_date = pd.to_datetime(c.get("exit_date")) if pd.notna(c.get("exit_date")) else c["date"]
            rr = c["exit_price"] / o["price_at_pick"] - 1
            sr = _ret_between(spy, o["date"], exit_date)
            realized.append({
                "picked": o["date"].date(), "exited": exit_date.date(),
                "mode": o["mode"], "ticker": o["ticker"],
                "entry": o["price_at_pick"], "exit": c["exit_price"],
                "reason": c.get("exit_reason"),
                "ret": rr, "spy": sr, "alpha": rr - sr,
            })
        if realized:
            rdf = pd.DataFrame(realized)
            print("\nRealized track record (closed picks):")
            with pd.option_context("display.max_rows", None, "display.width", 200,
                                   "display.float_format", lambda x: f"{x:+.1%}" if abs(x) < 10 else f"{x:,.2f}"):
                print(rdf.to_string(index=False))
            wins, losses = rdf[rdf["ret"] > 0], rdf[rdf["ret"] <= 0]
            print(f"\n  closed n={len(rdf)}  hit rate {len(wins)/len(rdf):.0%}  "
                  f"avg win {wins['ret'].mean() if len(wins) else 0:+.1%}  "
                  f"avg loss {losses['ret'].mean() if len(losses) else 0:+.1%}  "
                  f"avg alpha {rdf['alpha'].mean():+.1%}")
            for mode, g in rdf.groupby("mode"):
                print(f"  {mode:<8} n={len(g)}  ret {g['ret'].mean():+.1%}  alpha {g['alpha'].mean():+.1%}")

    if not passes.empty:
        print(f"\nPass runs recorded: {len(passes)} "
              f"({', '.join(passes['date'].dt.strftime('%Y-%m-%d') + ' ' + passes['mode'])})")

    # ── Open exposure vs the POLICY.md cap (only when sizes were recorded) ──
    open_mask = out["status"].isin(["OPEN", "AT_TARGET", "STOPPED", "EXPIRED"])
    open_keys = set(zip(out.loc[open_mask, "date"].astype(str),
                        out.loc[open_mask, "mode"], out.loc[open_mask, "ticker"]))
    sized = picks[picks["size_pct"].notna()] if "size_pct" in picks.columns else pd.DataFrame()
    if not sized.empty:
        open_sized = sized[[
            (str(r["date"].date()), r["mode"], r["ticker"]) in open_keys
            for _, r in sized.iterrows()]]
        exposure = open_sized["size_pct"].sum()
        flag = "  ** OVER CAP **" if exposure > MAX_TOTAL_EXPOSURE_PCT else ""
        print(f"\nOpen exposure (recorded size_pct): {exposure:.1f}% "
              f"vs POLICY.md cap {MAX_TOTAL_EXPOSURE_PCT:.0f}%{flag}")
        if exposure > MAX_TOTAL_EXPOSURE_PCT:
            alerts.append(f"EXPOSURE  total open size {exposure:.1f}% exceeds "
                          f"the {MAX_TOTAL_EXPOSURE_PCT:.0f}% cap (POLICY.md)")

    print("\nPer strategy/run (equal-weight mean):")
    grp = out.groupby(["mode", "kind", "date"]).agg(
        n=("ticker", "size"), ret=("ret", "mean"),
        spy=("spy", "mean"), alpha=("alpha", "mean"))
    for (mode, kind, date), g in grp.iterrows():
        print(f"  {date} {mode:<8} {kind:<7} n={int(g['n']):>2}  "
              f"ret {g['ret']:+.1%}  spy {g['spy']:+.1%}  alpha {g['alpha']:+.1%}")

    if alerts:
        print(f"\n{'='*70}\nALERTS — exit rules fired; reassess these picks "
              f"(take profit / close / re-underwrite):")
        for a in alerts:
            print(f"  {a}")
        print("Closing = append a kind=close row (see pick-protocol.md); never mutate.")
    else:
        print("\nNo exit-rule alerts.")

    print("\nScenario targets and returns are research bookkeeping, not financial advice.")

    if args.check and alerts:
        sys.exit(1)


if __name__ == "__main__":
    main()

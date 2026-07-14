#!/usr/bin/env python3
"""Local read-only web dashboard for the S&P 500 stock-pick funnel.

Serves a single-page UI on http://127.0.0.1:8765 that displays what is already
on disk — it never runs anything and never writes:
  - the latest shortlist ("top 50") table per mode  (output/<mode>/shortlist.csv),
  - funnel-stage attrition bars                     (output/<mode>/funnel.json),
  - the latest AI panel pick and top-10 ranking     (output/<mode>/final_*.md),
  - the picks ledger                                (picks/ledger.csv).

To refresh the data, run the skills in Claude Code: /stock-pick-momentum or
/stock-pick-dip (the UI shows copyable commands).

Stdlib only. Run:  python UI/dashboard.py  [--port 8765]
"""

import argparse
import csv
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
LEDGER = ROOT / "picks" / "ledger.csv"


def _read_csv(path):
    if not path.exists():
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def _read_text(path):
    return path.read_text() if path.exists() else ""


def _mtime(path):
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M") \
        if path.exists() else None


def read_state():
    modes = {}
    for mode in ("momentum", "dip"):
        d = OUTPUT / mode
        funnel = []
        if (d / "funnel.json").exists():
            funnel = json.loads((d / "funnel.json").read_text())
        modes[mode] = {
            "shortlist": _read_csv(d / "shortlist.csv"),
            "funnel": funnel,
            "final_pick_md": _read_text(d / "final_pick.md"),
            "final_ranking_md": _read_text(d / "final_ranking.md"),
            "screen_at": _mtime(d / "shortlist.csv"),
            "pick_at": _mtime(d / "final_pick.md"),
        }
    return {"modes": modes, "ledger": _read_csv(LEDGER)}


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>S&amp;P 500 Pick Funnel</title>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb;
  --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --baseline: #c3c2b7; --ring: rgba(11,11,11,0.10);
  --accent: #2a78d6; --mode-momentum: #2a78d6; --mode-dip: #1baf7a;
  --warning: #fab219; --good: #006300; --critical: #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19;
    --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --baseline: #383835; --ring: rgba(255,255,255,0.10);
    --accent: #3987e5; --mode-momentum: #3987e5; --mode-dip: #199e70;
    --good: #0ca30c;
  }
}
* { box-sizing: border-box; margin: 0; }
body {
  background: var(--page); color: var(--ink);
  font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
  padding: 24px; max-width: 1240px; margin: 0 auto;
}
h1 { font-size: 20px; font-weight: 650; }
h2 { font-size: 15px; font-weight: 600; margin: 0 0 10px; }
.sub { color: var(--ink-2); font-size: 13px; margin-top: 2px; }
.card {
  background: var(--surface); border: 1px solid var(--ring);
  border-radius: 10px; padding: 16px; margin-top: 16px;
}
.row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
button {
  font: inherit; color: var(--ink); background: var(--surface);
  border: 1px solid var(--baseline); border-radius: 8px;
  padding: 7px 14px; cursor: pointer;
}
button:hover:not(:disabled) { border-color: var(--accent); }
.hint { color: var(--muted); font-size: 12.5px; }
.hint code { font-family: ui-monospace, monospace; font-size: 12px; }
nav.tabs { display: flex; gap: 4px; margin-top: 20px; border-bottom: 1px solid var(--grid); }
nav.tabs button {
  border: none; background: none; border-radius: 8px 8px 0 0;
  padding: 8px 16px; color: var(--ink-2);
}
nav.tabs button.active {
  color: var(--ink); font-weight: 600;
  box-shadow: inset 0 -2px 0 var(--accent);
}
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.tile { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 12px 14px; }
.tile .label { color: var(--ink-2); font-size: 12.5px; }
.tile .value { font-size: 26px; font-weight: 600; margin-top: 2px; }
.tile .meta { color: var(--muted); font-size: 12px; margin-top: 2px; }
.funnel-row { display: grid; grid-template-columns: 210px 1fr; gap: 10px; align-items: center; margin: 5px 0; }
.funnel-row .stage { color: var(--ink-2); font-size: 12.5px; text-align: right; }
.funnel-bar-wrap { display: flex; align-items: center; gap: 8px; }
.funnel-bar { height: 18px; border-radius: 0 4px 4px 0; min-width: 2px; }
.funnel-count { font-size: 12.5px; color: var(--ink); font-variant-numeric: tabular-nums; }
.funnel-drop { color: var(--muted); font-size: 12px; }
.tablewrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
th {
  text-align: right; color: var(--muted); font-weight: 500;
  border-bottom: 1px solid var(--baseline); padding: 5px 8px;
  white-space: nowrap; cursor: pointer; user-select: none;
}
th.l, td.l { text-align: left; }
td {
  padding: 5px 8px; border-bottom: 1px solid var(--grid);
  text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap;
}
td.ticker { font-weight: 600; }
.meter { display: inline-flex; align-items: center; gap: 6px; }
.meter .track {
  width: 64px; height: 8px; border-radius: 4px;
  background: color-mix(in srgb, var(--accent) 22%, transparent);
}
.meter .fill { height: 8px; border-radius: 4px; background: var(--accent); display: block; }
.chip {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; color: var(--ink-2);
  border: 1px solid var(--grid); border-radius: 999px; padding: 1px 8px;
}
.chip .dot { width: 7px; height: 7px; border-radius: 50%; }
.flag { color: var(--ink-2); font-size: 11.5px; border: 1px solid var(--warning); border-radius: 999px; padding: 0 7px; }
details { margin-top: 12px; }
summary { cursor: pointer; color: var(--ink-2); font-weight: 550; }
.md { padding: 10px 4px; max-width: 860px; }
.md h1 { font-size: 17px; margin: 14px 0 6px; }
.md h2 { font-size: 15px; margin: 14px 0 6px; }
.md h3 { font-size: 13.5px; margin: 12px 0 4px; }
.md p, .md ul { margin: 6px 0; color: var(--ink-2); }
.md li { margin-left: 20px; }
.md strong { color: var(--ink); }
.md hr { border: none; border-top: 1px solid var(--grid); margin: 12px 0; }
.md code { background: var(--page); border: 1px solid var(--grid); border-radius: 4px; padding: 0 4px; font-size: 12px; }
.md table { margin: 8px 0; }
.cmd {
  display: inline-flex; gap: 8px; align-items: center;
  background: var(--page); border: 1px solid var(--grid); border-radius: 8px;
  padding: 5px 10px; font-family: ui-monospace, monospace; font-size: 12.5px;
}
section.tab { display: none; }
section.tab.active { display: block; }
</style>
</head>
<body>
<header>
  <h1>S&amp;P 500 pick funnel</h1>
  <div class="sub" id="freshness">loading…</div>
</header>

<div class="card">
  <div class="row">
    <span class="hint">Read-only view of <code>output/</code> and <code>picks/ledger.csv</code>.
      To refresh, run in Claude Code:</span>
    <span class="cmd">/stock-pick-momentum <button data-copy="/stock-pick-momentum">copy</button></span>
    <span class="cmd">/stock-pick-dip <button data-copy="/stock-pick-dip">copy</button></span>
  </div>
</div>

<nav class="tabs">
  <button data-tab="momentum" class="active">Momentum</button>
  <button data-tab="dip">Dip</button>
  <button data-tab="ledger">Picks ledger</button>
</nav>

<section class="tab active" id="tab-momentum"></section>
<section class="tab" id="tab-dip"></section>
<section class="tab" id="tab-ledger"></section>

<script>
"use strict";
const $ = (s, el) => (el || document).querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const isDark = () => matchMedia("(prefers-color-scheme: dark)").matches;
// ordinal blue ramp (light: steps 250-650; dark: 100-450 so no step darker than 600)
const RAMP_L = ["#86b6ef","#6da7ec","#5598e7","#3987e5","#2a78d6","#256abf","#1c5cab","#184f95","#104281"];
const RAMP_D = ["#cde2fb","#b7d3f6","#9ec5f4","#86b6ef","#6da7ec","#5598e7","#3987e5","#2a78d6","#256abf"];
const MODE_HUE = { momentum: "var(--mode-momentum)", dip: "var(--mode-dip)" };

const fmt = {
  pct(v, d=1) { const n = parseFloat(v); return isNaN(n) ? "–" : (n*100).toFixed(d) + "%"; },
  spct(v, d=1) { const n = parseFloat(v); return isNaN(n) ? "–" : (n>0?"+":"") + (n*100).toFixed(d) + "%"; },
  num(v, d=1) { const n = parseFloat(v); return isNaN(n) ? "–" : n.toFixed(d); },
  cap(v) {
    const n = parseFloat(v); if (isNaN(n)) return "–";
    return n >= 1e12 ? (n/1e12).toFixed(2)+"T" : (n/1e9).toFixed(0)+"B";
  },
  usd(v) { const n = parseFloat(v); return isNaN(n) ? "–" : "$" + n.toLocaleString(undefined, {maximumFractionDigits: 2}); },
};

// -- minimal markdown renderer (headers, bold/italic/code, lists, hr, tables)
function inlineMd(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|\W)\*([^*\n]+)\*(?=\W|$)/g, "$1<em>$2</em>");
}
function renderMd(text) {
  const out = [];
  const lines = text.split("\n");
  let list = false, para = [];
  const flush = () => { if (para.length) { out.push("<p>" + inlineMd(para.join(" ")) + "</p>"); para = []; } };
  const endList = () => { if (list) { out.push("</ul>"); list = false; } };
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i];
    const h = ln.match(/^(#{1,3})\s+(.*)/);
    if (h) { flush(); endList(); out.push(`<h${h[1].length}>${inlineMd(h[2])}</h${h[1].length}>`); continue; }
    if (/^\s*(---+|\*\*\*+)\s*$/.test(ln)) { flush(); endList(); out.push("<hr>"); continue; }
    if (/^\s*[-*]\s+/.test(ln)) {
      flush();
      if (!list) { out.push("<ul>"); list = true; }
      out.push("<li>" + inlineMd(ln.replace(/^\s*[-*]\s+/, "")) + "</li>");
      continue;
    }
    if (/^\s*\|.*\|\s*$/.test(ln)) {
      flush(); endList();
      const rows = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) { rows.push(lines[i]); i++; }
      i--;
      const cells = r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => inlineMd(c.trim()));
      let html = '<div class="tablewrap"><table>';
      rows.forEach((r, ri) => {
        if (/^\s*\|[\s:|-]+\|\s*$/.test(r)) return;
        const tag = ri === 0 ? "th" : "td";
        html += "<tr>" + cells(r).map(c => `<${tag} class="l">${c}</${tag}>`).join("") + "</tr>";
      });
      out.push(html + "</table></div>");
      continue;
    }
    if (ln.trim() === "") { flush(); endList(); continue; }
    para.push(ln.trim());
  }
  flush(); endList();
  return out.join("\n");
}

function tile(label, value, meta) {
  return `<div class="tile"><div class="label">${esc(label)}</div>` +
         `<div class="value">${value}</div><div class="meta">${esc(meta || "")}</div></div>`;
}

function funnelChart(stages) {
  if (!stages.length) return '<p class="hint">no funnel.json yet — run the screen</p>';
  const ramp = isDark() ? RAMP_D : RAMP_L;
  const max = Math.max(...stages.map(s => s.out), 1);
  return stages.map((s, i) => {
    const color = ramp[Math.min(i, ramp.length - 1)];
    const w = Math.max(100 * s.out / max, 0.5);
    const tip = `${s.stage}: ${s.in} in → ${s.out} out (−${s.dropped})`;
    return `<div class="funnel-row" title="${esc(tip)}">
      <div class="stage">${esc(s.stage)}</div>
      <div class="funnel-bar-wrap">
        <div class="funnel-bar" style="width:${w}%;background:${color}"></div>
        <span class="funnel-count">${s.out}</span>
        <span class="funnel-drop">−${s.dropped}</span>
      </div></div>`;
  }).join("");
}

const COLS = [
  { k: "rank", h: "#", f: v => v, cls: "" },
  { k: "ticker", h: "Ticker", f: esc, cls: "l ticker" },
  { k: "security", h: "Company", f: esc, cls: "l" },
  { k: "gics_sector", h: "Sector", f: esc, cls: "l" },
  { k: "composite_score", h: "Composite", f: v => {
      const n = parseFloat(v) || 0;
      return `<span class="meter"><span class="track"><span class="fill" style="width:${(n*100).toFixed(0)}%"></span></span>${(n*100).toFixed(1)}</span>`;
    }, cls: "" },
  { k: "marketCap", h: "Mkt cap", f: fmt.cap, cls: "" },
  { k: "dist_sma200", h: "vs 200d SMA", f: fmt.spct, cls: "" },
  { k: "dist_52w_high", h: "vs 52w high", f: fmt.spct, cls: "" },
  { k: "ret_12m", h: "12m ret", f: fmt.spct, cls: "" },
  { k: "analyst_upside", h: "Analyst upside", f: fmt.spct, cls: "" },
  { k: "forwardPE", h: "Fwd P/E", f: v => fmt.num(v, 1), cls: "" },
  { k: "rev_growth_ttm", h: "Rev growth", f: fmt.spct, cls: "" },
  { k: "operatingMargins", h: "Op margin", f: fmt.pct, cls: "" },
  { k: "returnOnEquity", h: "ROE", f: fmt.pct, cls: "" },
  { k: "net_debt_ebitda", h: "NetDebt/EBITDA", f: v => fmt.num(v, 2), cls: "" },
  { k: "eq_flags", h: "EQ flags", f: v => v ? v.split(";").map(x => `<span class="flag">⚠ ${esc(x)}</span>`).join(" ") : "", cls: "l" },
];

function shortlistTable(rows, mode) {
  const sortState = { key: "rank", asc: true };
  const id = `sl-${mode}`;
  const render = () => {
    const sorted = [...rows].sort((a, b) => {
      const av = parseFloat(a[sortState.key]), bv = parseFloat(b[sortState.key]);
      const cmp = (isNaN(av) || isNaN(bv))
        ? String(a[sortState.key] ?? "").localeCompare(String(b[sortState.key] ?? ""))
        : av - bv;
      return sortState.asc ? cmp : -cmp;
    });
    let html = "<table><thead><tr>" + COLS.map(c =>
      `<th class="${c.cls.includes("l") ? "l" : ""}" data-k="${c.k}">${c.h}${sortState.key===c.k ? (sortState.asc?" ↑":" ↓") : ""}</th>`
    ).join("") + "</tr></thead><tbody>";
    for (const r of sorted)
      html += "<tr>" + COLS.map(c => `<td class="${c.cls}">${c.f(r[c.k])}</td>`).join("") + "</tr>";
    $("#" + id).innerHTML = html + "</tbody></table>";
    $("#" + id).querySelectorAll("th").forEach(th => th.onclick = () => {
      const k = th.dataset.k;
      if (sortState.key === k) sortState.asc = !sortState.asc;
      else { sortState.key = k; sortState.asc = true; }
      render();
    });
  };
  setTimeout(render, 0);
  return `<div class="tablewrap" id="${id}"></div>`;
}

function latest(ledger, mode, kind, rank) {
  const rows = ledger.filter(r => r.mode === mode && r.kind === kind && (!rank || r.rank === String(rank)));
  return rows.length ? rows[rows.length - 1] : null;
}

function renderMode(mode, m, ledger) {
  const single = latest(ledger, mode, "single");
  const top1 = latest(ledger, mode, "rank10", 1);
  const tiles = [
    single ? tile("Latest single pick", esc(single.ticker), `${fmt.usd(single.price_at_pick)} at pick · ${single.date}`) : tile("Latest single pick", "–", ""),
    top1 ? tile("Panel top-10 #1", esc(top1.ticker), `${fmt.usd(top1.price_at_pick)} at pick · ${top1.date}`) : tile("Panel top-10 #1", "–", ""),
    tile("Shortlist names", String(m.shortlist.length), `screen run ${m.screen_at || "never"}`),
    tile("AI pick written", m.pick_at ? "✓" : "–", m.pick_at || "run /stock-pick-" + mode),
  ].join("");
  return `
  <div class="tiles" style="margin-top:16px">${tiles}</div>
  <div class="card"><h2>Funnel attrition — survivors per stage</h2>${funnelChart(m.funnel)}</div>
  <div class="card"><h2>Shortlist — top ${m.shortlist.length} by ${mode} composite</h2>
    ${shortlistTable(m.shortlist, mode)}
  </div>
  <div class="card">
    <h2>AI panel output</h2>
    <details open><summary>Final pick (final_pick.md · ${m.pick_at || "missing"})</summary>
      <div class="md">${m.final_pick_md ? renderMd(m.final_pick_md) : '<p class="hint">not generated yet</p>'}</div>
    </details>
    <details><summary>Ranked top-10 (final_ranking.md)</summary>
      <div class="md">${m.final_ranking_md ? renderMd(m.final_ranking_md) : '<p class="hint">not generated yet</p>'}</div>
    </details>
  </div>`;
}

function renderLedger(ledger) {
  const rows = [...ledger].reverse();
  let html = `<div class="card"><h2>Picks ledger — ${rows.length} rows, newest first</h2><div class="tablewrap"><table><thead><tr>
    <th class="l">Date</th><th class="l">Mode</th><th class="l">Kind</th><th>#</th><th class="l">Ticker</th>
    <th>Price@pick</th><th>Base target</th><th>EV price</th><th>Exit</th><th class="l">Thesis</th>
  </tr></thead><tbody>`;
  for (const r of rows) {
    const hue = MODE_HUE[r.mode] || "var(--muted)";
    html += `<tr>
      <td class="l">${esc(r.date)}</td>
      <td class="l"><span class="chip"><span class="dot" style="background:${hue}"></span>${esc(r.mode)}</span></td>
      <td class="l">${esc(r.kind)}</td><td>${esc(r.rank)}</td>
      <td class="l ticker">${esc(r.ticker)}</td>
      <td>${fmt.usd(r.price_at_pick)}</td>
      <td>${r.base_target ? fmt.usd(r.base_target) : "–"}</td>
      <td>${r.ev_price ? fmt.usd(r.ev_price) : "–"}</td>
      <td>${r.exit_price ? fmt.usd(r.exit_price) : "–"}</td>
      <td class="l" style="white-space:normal;min-width:340px">${esc(r.thesis)}</td>
    </tr>`;
  }
  return html + "</tbody></table></div></div>";
}

async function loadState() {
  const st = await (await fetch("/api/state")).json();
  $("#freshness").textContent =
    `screen: momentum ${st.modes.momentum.screen_at || "never"} · dip ${st.modes.dip.screen_at || "never"}` +
    ` — AI pick: momentum ${st.modes.momentum.pick_at || "never"} · dip ${st.modes.dip.pick_at || "never"}`;
  $("#tab-momentum").innerHTML = renderMode("momentum", st.modes.momentum, st.ledger);
  $("#tab-dip").innerHTML = renderMode("dip", st.modes.dip, st.ledger);
  $("#tab-ledger").innerHTML = renderLedger(st.ledger);
}

document.querySelectorAll("button[data-copy]").forEach(btn => btn.onclick = () => {
  navigator.clipboard.writeText(btn.dataset.copy);
  btn.textContent = "copied"; setTimeout(() => btn.textContent = "copy", 1200);
});
document.querySelectorAll("nav.tabs button").forEach(btn => btn.onclick = () => {
  document.querySelectorAll("nav.tabs button").forEach(b => b.classList.toggle("active", b === btn));
  document.querySelectorAll("section.tab").forEach(s => s.classList.toggle("active", s.id === "tab-" + btn.dataset.tab));
});

loadState();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            self._send(200, PAGE, "text/html")
        elif self.path == "/favicon.ico":
            svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><text y="13" font-size="13">📈</text></svg>'
            self._send(200, svg, "image/svg+xml")
        elif self.path == "/api/state":
            self._send(200, json.dumps(read_state()))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"pick-funnel dashboard → http://127.0.0.1:{args.port}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

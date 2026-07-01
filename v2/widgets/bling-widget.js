// Bling Empire — the forever widget (Scriptable).
//
// ONE script, many widgets. Add several Scriptable widgets and set each
// widget's "Parameter" (long-press widget -> Edit Widget -> Parameter):
//   brief      full daily brief (best on LARGE)          [default]
//   runway     money status (small)
//   positions  your trades: progress bars + stops (small/medium)
//   signals    today's actions + market pulse (medium)
// Lock-screen widgets (accessory sizes) auto-render a compact line.
//
// Live data: the API overlays fresh quotes on every refresh (~5-15 min).
// Offline-proof: last good payload is cached on-device; if the VPS is
// unreachable the widget shows cached data marked "offline".
//
// Setup: paste TOKEN from v2/.dashboard-creds, add widgets, done.

const URL_BASE = "http://187.127.113.131:3400";
const TOKEN = "PASTE_WIDGET_TOKEN_HERE";

// ── data with offline cache ────────────────────────────────────────────
const fm = FileManager.local();
const cachePath = fm.joinPath(fm.cacheDirectory(), "bling-widget.json");
let data = null, offline = false;
try {
  const req = new Request(`${URL_BASE}/api/widget?token=${TOKEN}&live=1`);
  req.timeoutInterval = 15;
  data = await req.loadJSON();
  fm.writeString(cachePath, JSON.stringify(data));
} catch (e) {
  offline = true;
  if (fm.fileExists(cachePath)) data = JSON.parse(fm.readString(cachePath));
}

const C = {
  bg: new Color("#f2ece0"), ink: new Color("#171512"), muted: new Color("#6b6358"),
  good: new Color("#0e9f6e"), bad: new Color("#c2410c"), accent: new Color("#14582f"),
  warn: new Color("#b45309"),
};
const mono = (s) => new Font("Menlo-Bold", s);
const bar = (p, n = 8) => "▓".repeat(Math.round(p * n)) + "░".repeat(n - Math.round(p * n));
const fmtK = (v) => `${Math.round(v / 1000)}k`;

const w = new ListWidget();
w.backgroundColor = C.bg;
w.setPadding(12, 13, 10, 13);
w.url = URL_BASE;

function line(text, size, color, options = {}) {
  const t = w.addText(text);
  t.font = options.mono ? mono(size) : (options.bold ? Font.boldSystemFont(size) : Font.systemFont(size));
  t.textColor = color;
  t.lineLimit = options.lines || 1;
  return t;
}

if (!data) {
  line("Bling: no data (server + no cache)", 11, C.bad, { lines: 3 });
} else {
  const family = config.widgetFamily || "large";
  const view = (args.widgetParameter || "brief").trim().toLowerCase();
  const isAccessory = family.startsWith("accessory");

  const runwayText = data.runway_months === null ? "∞" : `${data.runway_months} mo`;
  const alerts = data.holdings.filter((h) => h.stop_hit);

  const drawRunway = () => {
    line(`💰 Bling${offline ? " · offline" : ""}`, 10, C.muted, { bold: true });
    w.addSpacer(3);
    line(runwayText, 26, C.ink, { bold: true });
    line(`runway · ${fmtK(data.liquid)} liquid`, 10, C.muted);
    line(`burn ${fmtK(data.burn)}/mo · earn ${fmtK(data.income_target)}/mo`, 10, C.accent);
  };

  const drawPositions = (max) => {
    if (!data.holdings.length) { line("no open positions", 10, C.muted); return; }
    for (const h of data.holdings.slice(0, max)) {
      if (h.stop_hit) { line(`🔴 ${h.ticker} STOP ${h.stop} — SELL NOW`, 10, C.bad, { mono: true }); continue; }
      const day = h.day_pct !== null ? ` ${h.day_pct >= 0 ? "+" : ""}${h.day_pct}%` : "";
      const progress = h.progress !== null ? `${bar(h.progress)} ${Math.round(h.progress * 100)}%→${h.target}` : `${h.price ?? "?"}`;
      line(`${h.ticker} ${progress}${day}`, 10, (h.gain_pct ?? 0) >= 0 ? C.good : C.bad, { mono: true });
    }
  };

  const drawSignals = () => {
    if (data.buys.length) line(`🟢 BUY ${data.buys.join(" ")}`, 11, C.good, { bold: true, lines: 2 });
    if (data.sell_alerts.length) line(`🔴 ${data.sell_alerts.join(" ")}`, 11, C.bad, { bold: true });
    if (!data.buys.length && !data.sell_alerts.length) line("no new actions today", 10, C.muted);
    line(`👀 ${data.watch_count} watch · 〰 ${data.swing_count} swing setups`, 10, C.warn);
    if (data.markets.length) {
      const pulse = data.markets.map((m) =>
        `${m.label}${m.trend_up === false ? "▼" : "▲"}${m.day_pct >= 0 ? "+" : ""}${m.day_pct}`).join("  ");
      line(pulse, 9, C.muted, { mono: true });
    }
  };

  if (isAccessory) {
    // lock screen: one dense line — alerts beat everything
    if (alerts.length) line(`🔴 SELL ${alerts.map((h) => h.ticker).join(" ")}`, 12, C.bad, { bold: true });
    else if (data.buys.length) line(`🟢 ${data.buys[0]} · ${runwayText}`, 12, C.ink, { bold: true });
    else line(`💰 ${runwayText} · ${fmtK(data.liquid)}`, 12, C.ink, { bold: true });
  } else if (view === "runway") {
    drawRunway();
  } else if (view === "positions") {
    line(`positions${offline ? " · offline" : ""}`, 9, C.muted, { bold: true });
    w.addSpacer(3);
    drawPositions(family === "small" ? 3 : 6);
  } else if (view === "signals") {
    line(`signals · ${data.updated}${offline ? " · offline" : ""}`, 9, C.muted, { bold: true });
    w.addSpacer(3);
    drawSignals();
  } else { // brief
    drawRunway();
    w.addSpacer(6);
    drawPositions(family === "large" ? 6 : 3);
    w.addSpacer(6);
    drawSignals();
    w.addSpacer(4);
    line(`screen ${data.updated} · quotes ${data.generated_at}${offline ? " · OFFLINE CACHE" : ""}`, 8, C.muted);
  }
}

w.refreshAfterDate = new Date(Date.now() + 10 * 60 * 1000); // ask iOS for ~10 min refresh
Script.setWidget(w);
Script.complete();
if (config.runsInApp) w.presentLarge();

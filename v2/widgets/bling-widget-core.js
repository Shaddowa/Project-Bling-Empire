// ═════════════════════════════════════════════════════════════════════════
// Bling widget CORE — served by the dashboard at /api/widget-script.
// Edit THIS file on the VPS; every phone widget picks it up automatically
// (~10 min). BUMP CORE_VERSION so you can confirm rollout in the footer.
//
// WIDGET PARAMETER (long-press widget → Edit Widget → Parameter)
// ─────────────────────────────────────────────────────────────────────────
//   Comma-separated tokens. Each token is a VIEW, a FLAG, or key:value.
//
//   Views (pick one; default = brief)
//     brief       runway + positions + signals, the full daily picture
//     runway      big runway number, burn/earn, liquid + sparkline
//     positions   open positions with real progress bars
//     signals     today's BUY / SELL actions, watch + swing counts
//     pulse       market pulse rows (indices / macro tickers)
//
//   Key:value
//     positions:N   show at most N positions (1–12), e.g. "positions:5"
//     max:N         same as positions:N (combine with any view)
//
//   Flags
//     nopulse     hide the market-pulse line
//     nofooter    hide the timestamp footer
//     nospark     hide the sparkline
//     plain       text-only bars (no canvas drawing) — fastest render
//     dark|light  force appearance instead of following the system
//
//   Examples: "positions:5" · "brief,nopulse" · "runway" ·
//             "signals,nofooter" · "positions,max:3,plain"
//   Unknown tokens are IGNORED — a bad parameter never breaks the widget.
//
// Widget families supported: small · medium · large · extraLarge ·
// accessoryRectangular · accessoryCircular · accessoryInline (lock screen).
// ═════════════════════════════════════════════════════════════════════════
const CORE_VERSION = "3.0";

module.exports = async ({ URL_BASE, TOKEN }) => {

// ── safety kit: this widget must NEVER throw ──────────────────────────────
const num = (v, d = null) => (typeof v === "number" && isFinite(v) ? v : d);
const str = (v, d = "") => (typeof v === "string" ? v : d);
const arr = (v) => (Array.isArray(v) ? v : []);
const clamp01 = (v) => Math.max(0, Math.min(1, num(v, 0)));
const col = (hex, a) => { try { return a === undefined ? new Color(hex) : new Color(hex, a); } catch (e) { return new Color("#888888"); } };
const attempt = (fn, fallback = null) => { try { return fn(); } catch (e) { return fallback; } };

// ── parameter system v2 ───────────────────────────────────────────────────
const VIEWS = ["brief", "runway", "positions", "signals", "pulse"];
function parseParams(raw) {
  const P = { view: "brief", max: null, flags: {} };
  for (const piece of String(raw == null ? "" : raw).split(",")) {
    const tok = piece.trim().toLowerCase();
    if (!tok) continue;
    const i = tok.indexOf(":");
    const key = (i >= 0 ? tok.slice(0, i) : tok).trim();
    const val = i >= 0 ? tok.slice(i + 1).trim() : null;
    if (VIEWS.indexOf(key) >= 0) {
      P.view = key;
      if (key === "positions" && val) P.max = parseInt(val, 10);
    } else if (key === "max" || key === "n") {
      if (val) P.max = parseInt(val, 10);
    } else if (["nopulse", "nofooter", "nospark", "plain", "dark", "light"].indexOf(key) >= 0) {
      P.flags[key] = true;
    } // unknown tokens: ignored on purpose
  }
  P.max = num(P.max, null);
  if (P.max !== null) P.max = Math.max(1, Math.min(12, Math.round(P.max)));
  return P;
}
const P = parseParams(attempt(() => args.widgetParameter, ""));
const family = str(attempt(() => config.widgetFamily, "large"), "large") || "large";
const isAccessory = family.indexOf("accessory") === 0;

// ── data with offline cache + self-accumulated history (for sparkline) ────
const fm = FileManager.local();
const cachePath = fm.joinPath(fm.cacheDirectory(), "bling-widget.json");
const histPath = fm.joinPath(fm.cacheDirectory(), "bling-widget-history.json");
let data = null, offline = false;
try {
  const req = new Request(`${URL_BASE}/api/widget?token=${TOKEN}&live=1`);
  req.timeoutInterval = 15;
  data = await req.loadJSON();
  attempt(() => fm.writeString(cachePath, JSON.stringify(data)));
} catch (e) {
  offline = true;
  data = attempt(() => (fm.fileExists(cachePath) ? JSON.parse(fm.readString(cachePath)) : null));
}

// history: one sample ≥ 30 min apart, last 48 kept (~1–2 trading days)
let history = attempt(() => (fm.fileExists(histPath) ? JSON.parse(fm.readString(histPath)) : []), []) || [];
if (!Array.isArray(history)) history = [];
if (!offline && data) attempt(() => {
  const last = history[history.length - 1];
  if (!last || (Date.now() - num(last.t, 0)) > 30 * 60 * 1000) {
    history.push({ t: Date.now(), liquid: num(data.liquid, null), rw: num(data.runway_months, null) });
    history = history.slice(-48);
    fm.writeString(histPath, JSON.stringify(history));
  }
});

// ── palette: warm paper, light + dark variants ─────────────────────────────
let dark = attempt(() => Device.isUsingDarkAppearance(), false) === true;
if (P.flags.dark) dark = true;
if (P.flags.light) dark = false;
const C = dark ? {
  bgTop: "#26211a", bgBot: "#1a1611", ink: "#ede7da", muted: "#9a9184",
  good: "#34d399", bad: "#fb923c", accent: "#4ade80", warn: "#fbbf24",
  track: "#3d372c", barFrom: "#2ea36b", barTo: "#7fe0ad",
} : {
  bgTop: "#f6f1e7", bgBot: "#eee6d5", ink: "#171512", muted: "#6b6358",
  good: "#0e9f6e", bad: "#c2410c", accent: "#14582f", warn: "#b45309",
  track: "#e2dac7", barFrom: "#2ea36b", barTo: "#14582f",
};
const lerpHex = (h1, h2, t) => attempt(() => {
  const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [a, b] = [p(h1), p(h2)];
  return "#" + a.map((v, i) => Math.round(v + (b[i] - v) * clamp01(t)).toString(16).padStart(2, "0")).join("");
}, h1);
const mono = (s) => new Font("Menlo-Bold", s);
const serif = (s) => attempt(() => new Font("Georgia-Bold", s), Font.boldSystemFont(s)); // Fraunces-adjacent brand serif

// ── widget shell ───────────────────────────────────────────────────────────
const w = new ListWidget();
w.url = URL_BASE;
if (!isAccessory) {
  attempt(() => {
    const g = new LinearGradient();
    g.colors = [col(C.bgTop), col(C.bgBot)];
    g.locations = [0, 1];
    g.startPoint = new Point(0, 0);
    g.endPoint = new Point(0, 1);
    w.backgroundGradient = g;
  });
  w.backgroundColor = col(C.bgTop);
  w.setPadding(12, 13, 10, 13);
} else {
  w.setPadding(2, 2, 2, 2);
}

function line(on, text, size, colorHex, o = {}) {
  const t = on.addText(String(text));
  t.font = o.mono ? mono(size) : o.serif ? serif(size) : o.bold ? Font.boldSystemFont(size) : Font.systemFont(size);
  t.textColor = col(colorHex);
  t.lineLimit = o.lines || 1;
  if (o.shrink) t.minimumScaleFactor = 0.6;
  return t;
}
function icon(on, name, size, colorHex) {
  return attempt(() => {
    const s = SFSymbol.named(name);
    if (!s || !s.image) return null;
    attempt(() => s.applyFont(Font.systemFont(size)));
    const img = on.addImage(s.image);
    img.imageSize = new Size(size + 2, size + 2);
    img.tintColor = col(colorHex);
    img.resizable = true;
    return img;
  });
}

// ── DrawContext pieces ─────────────────────────────────────────────────────
// Rounded progress bar with gradient fill, red stop tick, green target cap.
function barImage(width, barH, frac, o = {}) {
  return attempt(() => {
    const H = barH + 4;
    const ctx = new DrawContext();
    ctx.size = new Size(width, H);
    ctx.opaque = false;
    ctx.respectScreenScale = true;
    const y = 2, r = barH / 2;
    const fillPath = (p, hex, a) => { ctx.setFillColor(col(hex, a)); ctx.addPath(p); ctx.fillPath(); };
    // track
    let p = new Path();
    p.addRoundedRect(new Rect(0, y, width, barH), r, r);
    fillPath(p, C.track);
    // gradient fill (colour-lerped slices under a rounded cap)
    const f = clamp01(frac);
    if (f > 0.005) {
      const fw = Math.max(barH, f * width);
      p = new Path();
      p.addRoundedRect(new Rect(0, y, fw, barH), r, r);
      fillPath(p, C.barFrom);
      const x0 = r, x1 = fw - r, slices = 18;
      for (let i = 0; i < slices && x1 > x0; i++) {
        const sx = x0 + ((x1 - x0) * i) / slices;
        const sw = (x1 - x0) / slices + 0.5;
        p = new Path();
        p.addRect(new Rect(sx, y, sw, barH));
        fillPath(p, lerpHex(C.barFrom, C.barTo, (i + 1) / slices));
      }
    }
    // red stop-loss tick
    if (o.stopFrac !== null && o.stopFrac !== undefined) {
      const sx = Math.max(1, Math.min(width - 2, clamp01(o.stopFrac) * width - 1));
      p = new Path();
      p.addRoundedRect(new Rect(sx, 0, 2, H), 1, 1);
      fillPath(p, C.bad);
    }
    // thin ink tick where cost sits (entry marker)
    if (o.costFrac !== null && o.costFrac !== undefined && o.costFrac > 0.02) {
      p = new Path();
      p.addRect(new Rect(clamp01(o.costFrac) * width - 0.5, y, 1, barH));
      fillPath(p, C.muted, 0.85);
    }
    // green target cap at the right end
    p = new Path();
    p.addRoundedRect(new Rect(width - 2.5, 0, 2.5, H), 1.2, 1.2);
    fillPath(p, C.accent);
    return ctx.getImage();
  });
}

// Tiny sparkline (polyline + end dot) from the self-accumulated history.
function sparkImage(width, height, values, hex) {
  return attempt(() => {
    const vs = values.filter((v) => num(v) !== null);
    if (vs.length < 2) return null;
    const ctx = new DrawContext();
    ctx.size = new Size(width, height);
    ctx.opaque = false;
    ctx.respectScreenScale = true;
    let lo = Math.min.apply(null, vs), hi = Math.max.apply(null, vs);
    if (hi - lo < 1e-9) { hi += 1; lo -= 1; }
    const pad = 2;
    const px = (i) => pad + ((width - 2 * pad) * i) / (vs.length - 1);
    const py = (v) => pad + (height - 2 * pad) * (1 - (v - lo) / (hi - lo));
    const p = new Path();
    vs.forEach((v, i) => (i === 0 ? p.move(new Point(px(i), py(v))) : p.addLine(new Point(px(i), py(v)))));
    ctx.setStrokeColor(col(hex));
    ctx.setLineWidth(1.5);
    ctx.addPath(p);
    ctx.strokePath();
    const dot = new Path();
    dot.addEllipse(new Rect(px(vs.length - 1) - 2, py(vs[vs.length - 1]) - 2, 4, 4));
    ctx.setFillColor(col(hex));
    ctx.addPath(dot);
    ctx.fillPath();
    return ctx.getImage();
  });
}

// Gauge ring (arc via line segments) for accessoryCircular.
function ringImage(d, frac, label, sub) {
  return attempt(() => {
    const ctx = new DrawContext();
    ctx.size = new Size(d, d);
    ctx.opaque = false;
    ctx.respectScreenScale = true;
    const lw = 5, r = d / 2 - lw / 2 - 1, cx = d / 2, cy = d / 2;
    const pt = (a) => new Point(cx + r * Math.sin(a), cy - r * Math.cos(a));
    const seg = (a0, a1, c, width) => {
      const p = new Path();
      const steps = Math.max(2, Math.ceil(((a1 - a0) / Math.PI) * 24));
      for (let i = 0; i <= steps; i++) {
        const a = a0 + ((a1 - a0) * i) / steps;
        i === 0 ? p.move(pt(a)) : p.addLine(pt(a));
      }
      ctx.setStrokeColor(c);
      ctx.setLineWidth(width);
      ctx.addPath(p);
      ctx.strokePath();
    };
    const capDot = (a, c) => {
      const q = pt(a), p = new Path();
      p.addEllipse(new Rect(q.x - lw / 2, q.y - lw / 2, lw, lw));
      ctx.setFillColor(c);
      ctx.addPath(p);
      ctx.fillPath();
    };
    seg(0, Math.PI * 2, col("#ffffff", 0.28), lw); // track (lock screen tints it)
    const f = clamp01(frac);
    if (f > 0.02) {
      const end = Math.PI * 2 * f;
      seg(0, end, col("#ffffff"), lw);
      capDot(0, col("#ffffff"));
      capDot(end, col("#ffffff"));
    }
    ctx.setTextAlignedCenter();
    ctx.setTextColor(col("#ffffff"));
    ctx.setFont(Font.boldSystemFont(sub ? 15 : 17));
    ctx.drawTextInRect(String(label), new Rect(0, cy - (sub ? 13 : 10), d, 20));
    if (sub) {
      ctx.setFont(Font.systemFont(8));
      ctx.setTextColor(col("#ffffff", 0.75));
      ctx.drawTextInRect(String(sub), new Rect(0, cy + 4, d, 11));
    }
    return ctx.getImage();
  });
}

// ── derived data (all defensive) ───────────────────────────────────────────
const D = data ? (() => {
  const holdings = arr(data.holdings).filter((h) => h && typeof h === "object" && str(h.ticker));
  const rw = num(data.runway_months, null);
  const dayPcts = holdings.map((h) => num(h.day_pct)).filter((v) => v !== null);
  return {
    rw,
    rwText: rw === null ? "∞" : `${Math.round(rw * 10) / 10} mo`,
    rwFrac: rw === null ? 1 : clamp01(rw / 12), // 12-month runway = full gauge
    liquid: num(data.liquid, 0),
    burn: num(data.burn, 0),
    income: num(data.income_target, 0),
    holdings,
    alerts: holdings.filter((h) => !!h.stop_hit),
    buys: arr(data.buys).map((b) => str(b, String(b))).filter(Boolean),
    sells: arr(data.sell_alerts).map((s) => str(s, String(s))).filter(Boolean),
    watch: num(data.watch_count, 0),
    swing: num(data.swing_count, 0),
    markets: arr(data.markets).filter((m) => m && typeof m === "object"),
    updated: str(data.updated) || "—",
    genAt: str(data.generated_at) || "—",
    dayAvg: dayPcts.length ? dayPcts.reduce((a, b) => a + b, 0) / dayPcts.length : null,
  };
})() : null;

const fmtK = (v) => `${Math.round(num(v, 0) / 1000)}k`;
const pct = (v) => (v === null ? "" : `${v >= 0 ? "+" : ""}${Math.round(v * 10) / 10}%`);
const textBar = (p, n = 8) => "▓".repeat(Math.round(clamp01(p) * n)) + "░".repeat(n - Math.round(clamp01(p) * n));

// Bar geometry for one holding: range min(stop,cost)→target, price fills it.
function barSpec(h) {
  const price = num(h.price), cost = num(h.cost), stop = num(h.stop), target = num(h.target);
  if (price === null || target === null) return null;
  const base = cost !== null ? cost : price;
  const lo = stop !== null ? Math.min(stop, base) : base;
  if (!(target > lo)) return null;
  const span = target - lo;
  return {
    frac: clamp01((price - lo) / span),
    stopFrac: stop !== null ? clamp01((stop - lo) / span) : null,
    costFrac: cost !== null ? clamp01((cost - lo) / span) : null,
  };
}

// ── building blocks ────────────────────────────────────────────────────────
function header(on, title) {
  const h = on.addStack();
  h.layoutHorizontally();
  h.centerAlignContent();
  icon(h, "chart.line.uptrend.xyaxis", 10, C.accent);
  h.addSpacer(4);
  line(h, title, 10, C.muted, { bold: true });
  h.addSpacer();
  line(h, `${D ? D.updated : ""}${offline ? " · offline" : ""}`, 9, offline ? C.warn : C.muted);
}

function positionRow(on, h, barWidth) {
  const v = on.addStack();
  v.layoutVertically();
  if (h.stop_hit) {
    const r = v.addStack();
    r.layoutHorizontally();
    r.centerAlignContent();
    icon(r, "exclamationmark.triangle.fill", 10, C.bad);
    r.addSpacer(3);
    line(r, `${str(h.ticker, "?")} STOP ${num(h.stop, 0)} — SELL NOW`, 11, C.bad, { mono: true, shrink: true });
    return;
  }
  const top = v.addStack();
  top.layoutHorizontally();
  top.centerAlignContent();
  line(top, str(h.ticker, "?"), 11, C.ink, { mono: true });
  top.addSpacer();
  const day = num(h.day_pct), gain = num(h.gain_pct);
  if (day !== null) line(top, pct(day), 10, day >= 0 ? C.good : C.bad, { mono: true });
  if (gain !== null) {
    top.addSpacer(6);
    line(top, `${pct(gain)} all`, 9, gain >= 0 ? C.accent : C.bad);
  }
  if (day === null && gain === null) line(top, `${num(h.price, "?")}`, 10, C.muted, { mono: true });
  const spec = barSpec(h);
  const frac = spec ? spec.frac : num(h.progress);
  if (frac !== null && !P.flags.plain) {
    v.addSpacer(2);
    const img = barImage(barWidth, 6, frac, spec || {});
    if (img) {
      const wi = v.addImage(img);
      wi.imageSize = new Size(barWidth, 10);
    } else {
      line(v, textBar(frac), 9, C.accent, { mono: true });
    }
  } else if (frac !== null) {
    line(v, `${textBar(frac)} ${Math.round(clamp01(frac) * 100)}%→${num(h.target, "?")}`, 9, C.accent, { mono: true });
  }
}

function positionsBlock(on, max, barWidth) {
  if (!D.holdings.length) { line(on, "no open positions", 10, C.muted); return; }
  D.holdings.slice(0, max).forEach((h, i) => {
    if (i) on.addSpacer(5);
    positionRow(on, h, barWidth);
  });
}

function signalsBlock(on, o = {}) {
  if (D.buys.length) {
    const r = on.addStack();
    r.layoutHorizontally();
    r.centerAlignContent();
    icon(r, "arrow.up.circle.fill", 11, C.good);
    r.addSpacer(3);
    line(r, `BUY ${D.buys.join(" ")}`, 11, C.good, { bold: true, lines: 2, shrink: true });
  }
  if (D.sells.length) {
    const r = on.addStack();
    r.layoutHorizontally();
    r.centerAlignContent();
    icon(r, "arrow.down.circle.fill", 11, C.bad);
    r.addSpacer(3);
    line(r, D.sells.join(" "), 11, C.bad, { bold: true, shrink: true });
  }
  if (!D.buys.length && !D.sells.length) line(on, "no new actions today", 10, C.muted);
  on.addSpacer(2);
  line(on, `👀 ${D.watch} watch · 〰 ${D.swing} swing setups`, 10, C.warn);
  if (!o.noPulse && !P.flags.nopulse && D.markets.length) {
    on.addSpacer(2);
    pulseLine(on);
  }
}

function pulseLine(on) {
  const txt = D.markets.map((m) => {
    const dp = num(m.day_pct, 0);
    return `${str(m.label, "?")}${m.trend_up === false ? "▼" : "▲"}${dp >= 0 ? "+" : ""}${dp}`;
  }).join("  ");
  line(on, txt, 9, C.muted, { mono: true, shrink: true });
}

function runwayHero(on, big) {
  const r = on.addStack();
  r.layoutHorizontally();
  r.bottomAlignContent();
  line(r, D.rwText, big, C.ink, { serif: true, shrink: true });
  r.addSpacer(6);
  const rc = r.addStack();
  rc.layoutVertically();
  line(rc, "runway", 9, C.muted, { bold: true });
  line(rc, `${fmtK(D.liquid)} liquid`, 9, C.accent);
  on.addSpacer(2);
  line(on, `burn ${fmtK(D.burn)}/mo · earn ${fmtK(D.income)}/mo`, 10, C.muted);
}

function sparkBlock(on, width, height, label) {
  if (P.flags.nospark) return false;
  const img = sparkImage(width, height, history.map((p) => num(p && p.liquid)), C.accent);
  if (!img) return false;
  const wi = on.addImage(img);
  wi.imageSize = new Size(width, height);
  if (label) line(on, label, 8, C.muted);
  return true;
}

function footer(on) {
  if (P.flags.nofooter) return;
  on.addSpacer(3);
  line(on, `screen ${D.updated} · quotes ${D.genAt} · v${CORE_VERSION}${offline ? " · OFFLINE" : ""}`, 8, C.muted, { shrink: true });
}

// ── per-family renderers ───────────────────────────────────────────────────
function renderSmall() {
  if (P.view === "positions") {
    header(w, "positions");
    w.addSpacer(4);
    positionsBlock(w, P.max || 3, 122);
  } else if (P.view === "signals") {
    header(w, "signals");
    w.addSpacer(4);
    signalsBlock(w, { noPulse: true });
  } else if (P.view === "pulse") {
    header(w, "pulse");
    w.addSpacer(4);
    if (!D.markets.length) line(w, "no pulse data", 10, C.muted);
    D.markets.slice(0, 4).forEach((m) => {
      const dp = num(m.day_pct, 0);
      line(w, `${str(m.label, "?")} ${dp >= 0 ? "+" : ""}${dp}%`, 11, m.trend_up === false ? C.bad : C.good, { mono: true });
    });
  } else { // brief + runway
    header(w, "Bling");
    w.addSpacer(2);
    line(w, D.rwText, 27, C.ink, { serif: true, shrink: true });
    line(w, `runway · ${fmtK(D.liquid)} liquid`, 9, C.muted);
    w.addSpacer(3);
    if (!P.flags.plain) {
      const img = barImage(122, 6, D.rwFrac, {});
      if (img) { const wi = w.addImage(img); wi.imageSize = new Size(122, 10); }
    }
    w.addSpacer(3);
    if (D.alerts.length) line(w, `🔴 SELL ${D.alerts.map((h) => str(h.ticker, "?")).join(" ")}`, 10, C.bad, { bold: true, shrink: true });
    else if (D.buys.length) line(w, `🟢 BUY ${D.buys.join(" ")}`, 10, C.good, { bold: true, shrink: true });
    else line(w, `burn ${fmtK(D.burn)} · earn ${fmtK(D.income)}`, 9, C.accent);
  }
  w.addSpacer();
}

function renderMedium() {
  if (P.view === "brief") {
    header(w, "Bling");
    w.addSpacer(4);
    const cols = w.addStack();
    cols.layoutHorizontally();
    const left = cols.addStack();
    left.layoutVertically();
    runwayHero(left, 24);
    left.addSpacer(4);
    if (D.alerts.length) line(left, `🔴 SELL ${D.alerts.map((h) => str(h.ticker, "?")).join(" ")}`, 10, C.bad, { bold: true, shrink: true });
    else if (D.buys.length) line(left, `🟢 BUY ${D.buys.join(" ")}`, 10, C.good, { bold: true, shrink: true });
    else line(left, `👀 ${D.watch} watch · 〰 ${D.swing}`, 9, C.warn);
    cols.addSpacer(14);
    const right = cols.addStack();
    right.layoutVertically();
    if (D.holdings.length) positionsBlock(right, P.max || 3, 140);
    else { sparkBlock(right, 140, 34, "liquid trend"); if (!P.flags.nopulse && D.markets.length) { right.addSpacer(4); pulseLine(right); } }
    w.addSpacer();
    if (!P.flags.nopulse && D.holdings.length && D.markets.length) pulseLine(w);
  } else if (P.view === "runway") {
    header(w, "runway");
    w.addSpacer(4);
    const cols = w.addStack();
    cols.layoutHorizontally();
    const left = cols.addStack();
    left.layoutVertically();
    runwayHero(left, 28);
    cols.addSpacer(14);
    const right = cols.addStack();
    right.layoutVertically();
    right.addSpacer(4);
    sparkBlock(right, 130, 40, "liquid trend");
    w.addSpacer();
  } else if (P.view === "positions") {
    header(w, "positions");
    w.addSpacer(4);
    const n = Math.min(P.max || 4, 4);
    if (D.holdings.length > 2 && n > 2) { // two columns
      const cols = w.addStack();
      cols.layoutHorizontally();
      const a = cols.addStack(); a.layoutVertically();
      cols.addSpacer(14);
      const b = cols.addStack(); b.layoutVertically();
      D.holdings.slice(0, n).forEach((h, i) => {
        const c = i % 2 === 0 ? a : b;
        if (i > 1) c.addSpacer(5);
        positionRow(c, h, 138);
      });
    } else positionsBlock(w, n, 300);
    w.addSpacer();
  } else if (P.view === "pulse") {
    header(w, "pulse");
    w.addSpacer(4);
    if (!D.markets.length) line(w, "no pulse data", 10, C.muted);
    D.markets.slice(0, 4).forEach((m) => {
      const dp = num(m.day_pct, 0);
      const r = w.addStack();
      r.layoutHorizontally();
      line(r, str(m.label, "?"), 11, C.ink, { mono: true });
      r.addSpacer();
      line(r, `${dp >= 0 ? "+" : ""}${dp}%`, 11, m.trend_up === false ? C.bad : C.good, { mono: true });
    });
    w.addSpacer();
  } else { // signals
    header(w, "signals");
    w.addSpacer(4);
    signalsBlock(w);
    w.addSpacer();
  }
  footer(w);
}

function renderLarge(xl) {
  header(w, "Bling Empire");
  w.addSpacer(6);
  if (P.view === "runway") {
    runwayHero(w, 40);
    w.addSpacer(8);
    sparkBlock(w, xl ? 300 : 220, 50, "liquid trend (self-recorded ~30 min samples)");
    w.addSpacer(8);
    line(w, `income target ${fmtK(D.income)}/mo`, 11, C.accent, { bold: true });
    if (D.dayAvg !== null) line(w, `positions today avg ${pct(D.dayAvg)}`, 10, D.dayAvg >= 0 ? C.good : C.bad);
  } else if (P.view === "positions") {
    positionsBlock(w, P.max || (xl ? 10 : 7), xl ? 380 : 300);
  } else if (P.view === "signals") {
    signalsBlock(w);
    w.addSpacer(6);
    line(w, `runway ${D.rwText} · liquid ${fmtK(D.liquid)}`, 10, C.muted);
  } else if (P.view === "pulse") {
    if (!D.markets.length) line(w, "no pulse data", 10, C.muted);
    D.markets.slice(0, 8).forEach((m) => {
      const dp = num(m.day_pct, 0);
      const r = w.addStack();
      r.layoutHorizontally();
      line(r, str(m.label, "?"), 12, C.ink, { mono: true });
      r.addSpacer();
      line(r, `${dp >= 0 ? "+" : ""}${dp}%`, 12, m.trend_up === false ? C.bad : C.good, { mono: true });
      w.addSpacer(3);
    });
  } else if (xl) { // brief, extraLarge: two columns
    const cols = w.addStack();
    cols.layoutHorizontally();
    const left = cols.addStack();
    left.layoutVertically();
    runwayHero(left, 30);
    left.addSpacer(8);
    positionsBlock(left, P.max || 8, 250);
    cols.addSpacer(24);
    const right = cols.addStack();
    right.layoutVertically();
    sparkBlock(right, 220, 44, "liquid trend");
    right.addSpacer(8);
    signalsBlock(right);
    cols.addSpacer();
  } else { // brief, large
    const hero = w.addStack();
    hero.layoutHorizontally();
    hero.bottomAlignContent();
    const hl = hero.addStack();
    hl.layoutVertically();
    runwayHero(hl, 28);
    hero.addSpacer();
    const hr = hero.addStack();
    hr.layoutVertically();
    sparkBlock(hr, 96, 30, "liquid");
    w.addSpacer(8);
    positionsBlock(w, P.max || 5, 300);
    w.addSpacer(8);
    signalsBlock(w);
  }
  w.addSpacer();
  footer(w);
}

// lock screen: alerts beat buys beat runway, always
function accessoryLine() {
  if (D.alerts.length) return { text: `SELL ${D.alerts.map((h) => str(h.ticker, "?")).join(" ")}`, sym: "exclamationmark.triangle.fill" };
  if (D.sells.length) return { text: `SELL ${D.sells.join(" ")}`, sym: "exclamationmark.triangle.fill" };
  if (D.buys.length) return { text: `BUY ${D.buys[0]} · ${D.rwText}`, sym: "arrow.up.circle.fill" };
  return { text: `${D.rwText} · ${fmtK(D.liquid)}`, sym: "chart.line.uptrend.xyaxis" };
}

function renderAccessoryInline() {
  const a = accessoryLine();
  const s = w.addStack();
  s.layoutHorizontally();
  s.centerAlignContent();
  icon(s, a.sym, 11, C.ink);
  s.addSpacer(3);
  line(s, a.text, 12, C.ink, { bold: true });
}

function renderAccessoryRectangular() {
  const a = accessoryLine();
  const s = w.addStack();
  s.layoutVertically();
  const r1 = s.addStack();
  r1.layoutHorizontally();
  r1.centerAlignContent();
  icon(r1, a.sym, 11, C.ink);
  r1.addSpacer(3);
  line(r1, a.text, 13, C.ink, { bold: true, shrink: true });
  s.addSpacer(1);
  line(s, `burn ${fmtK(D.burn)}/mo · ${D.watch}👀 ${D.swing}〰${offline ? " · off" : ""}`, 10, C.ink, { shrink: true });
  s.addSpacer(2);
  const img = P.flags.plain ? null : barImage(148, 5, P.view === "positions" && D.holdings.length ? (barSpec(D.holdings[0]) || { frac: num(D.holdings[0].progress, 0) }).frac : D.rwFrac, {});
  if (img) { const wi = s.addImage(img); wi.imageSize = new Size(148, 9); }
  else line(s, textBar(D.rwFrac, 12), 9, C.ink, { mono: true });
}

function renderAccessoryCircular() {
  let frac = D.rwFrac, label = D.rw === null ? "∞" : String(Math.round(D.rw)), sub = "mo";
  if (P.view === "positions" && D.holdings.length) {
    const h = D.holdings[0];
    const spec = barSpec(h) || { frac: num(h.progress, 0) };
    frac = spec.frac;
    label = `${Math.round(clamp01(frac) * 100)}`;
    sub = str(h.ticker, "").slice(0, 6) || "%";
  }
  if (D.alerts.length) { label = "SELL"; sub = str(D.alerts[0].ticker, "").slice(0, 6); frac = 1; }
  const img = ringImage(76, frac, label, sub);
  if (img) {
    const wi = w.addImage(img);
    wi.imageSize = new Size(60, 60);
    attempt(() => { wi.centerAlignImage(); });
  } else line(w, label, 14, C.ink, { bold: true });
}

// ── main (never throw) ─────────────────────────────────────────────────────
try {
  if (!data) {
    if (isAccessory) line(w, "Bling: no data", 12, C.ink, { lines: 2 });
    else {
      header(w, "Bling");
      w.addSpacer(4);
      line(w, "no data", 16, C.ink, { serif: true });
      line(w, "server unreachable + no cache yet", 10, C.muted, { lines: 3 });
      w.addSpacer();
    }
  } else if (family === "accessoryInline") renderAccessoryInline();
  else if (family === "accessoryCircular") renderAccessoryCircular();
  else if (family === "accessoryRectangular") renderAccessoryRectangular();
  else if (family === "small") renderSmall();
  else if (family === "medium") renderMedium();
  else renderLarge(family === "extraLarge");
} catch (e) {
  attempt(() => line(w, `Bling render error: ${e}`, 10, C.bad, { lines: 4 }));
}

attempt(() => { w.refreshAfterDate = new Date(Date.now() + 10 * 60 * 1000); }); // ~10 min refresh
Script.setWidget(w);
Script.complete();

if (attempt(() => config.runsInApp, false)) attempt(() => w.presentLarge());
};

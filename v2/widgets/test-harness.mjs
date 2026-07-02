// Node harness for bling-widget-core.js — stubs the Scriptable runtime and
// executes the core for EVERY widget family × parameter × payload scenario
// to prove it never throws. Stubs expose ONLY methods the real Scriptable
// API has, so calling a non-existent API surfaces as a failure here.
//
// Run: node /root/Project-Bling-Empire/v2/widgets/test-harness.mjs
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);

// ── Scriptable API stubs ───────────────────────────────────────────────────
class Color {
  constructor(hex, alpha) {
    if (typeof hex !== "string" || !/^#?[0-9a-fA-F]{3,8}$/.test(hex)) throw new Error(`bad Color hex: ${hex}`);
    this.hex = hex; this.alpha = alpha === undefined ? 1 : alpha;
  }
  static dynamic(l, d) { return l; }
}
class Font {
  constructor(name, size) { this.name = name; this.size = size; }
  static systemFont(s) { return new Font("system", s); }
  static boldSystemFont(s) { return new Font("system-bold", s); }
  static mediumSystemFont(s) { return new Font("system-medium", s); }
  static lightSystemFont(s) { return new Font("system-light", s); }
}
class Point { constructor(x, y) { this.x = x; this.y = y; } }
class Size { constructor(w, h) { this.width = w; this.height = h; } }
class Rect { constructor(x, y, w, h) { this.x = x; this.y = y; this.width = w; this.height = h; } }
class Image_ {}
class LinearGradient { constructor() { this.colors = []; this.locations = []; this.startPoint = null; this.endPoint = null; } }
class WidgetText {
  constructor(text) {
    if (typeof text !== "string") throw new Error("addText requires a string");
    this.text = text; this.font = null; this.textColor = null; this.lineLimit = 0;
    this.minimumScaleFactor = 1; this.url = null; this.textOpacity = 1;
  }
  leftAlignText() {} centerAlignText() {} rightAlignText() {}
}
class WidgetImage {
  constructor(img) {
    if (!(img instanceof Image_)) throw new Error("addImage requires an Image");
    this.image = img; this.imageSize = null; this.tintColor = null; this.resizable = true; this.url = null;
  }
  leftAlignImage() {} centerAlignImage() {} rightAlignImage() {}
  applyFittingContentMode() {} applyFillingContentMode() {}
}
class WidgetStack {
  constructor() { this.items = []; this.spacing = 0; this.url = null; this.size = null; this.cornerRadius = 0; this.backgroundColor = null; this.backgroundGradient = null; }
  addText(t) { const x = new WidgetText(t); this.items.push(x); return x; }
  addImage(i) { const x = new WidgetImage(i); this.items.push(x); return x; }
  addSpacer(n) { if (n !== undefined && typeof n !== "number") throw new Error("addSpacer arg must be number"); this.items.push({ spacer: n ?? "flex" }); }
  addStack() { const s = new WidgetStack(); this.items.push(s); return s; }
  addDate(d) { this.items.push({ date: d }); return { font: null, textColor: null }; }
  setPadding(t, l, b, r) {}
  layoutHorizontally() {} layoutVertically() {}
  topAlignContent() {} centerAlignContent() {} bottomAlignContent() {}
}
class ListWidget extends WidgetStack {
  constructor() { super(); this.refreshAfterDate = null; }
  presentSmall() {} presentMedium() {} presentLarge() {} presentExtraLarge() {}
}
class Path {
  constructor() { this.ops = []; }
  move(p) { this.#pt(p); this.ops.push(["move", p]); }
  addLine(p) { this.#pt(p); this.ops.push(["line", p]); }
  addRect(r) { this.#rect(r); this.ops.push(["rect", r]); }
  addEllipse(r) { this.#rect(r); this.ops.push(["ellipse", r]); }
  addRoundedRect(r, cw, ch) { this.#rect(r); if (!isFinite(cw) || !isFinite(ch)) throw new Error("bad corner radius"); this.ops.push(["rrect", r]); }
  addLines(pts) { pts.forEach((p) => this.#pt(p)); }
  closeSubpath() {}
  #pt(p) { if (!(p instanceof Point) || !isFinite(p.x) || !isFinite(p.y)) throw new Error("bad Point"); }
  #rect(r) { if (!(r instanceof Rect) || ![r.x, r.y, r.width, r.height].every(isFinite)) throw new Error("bad Rect"); }
}
class DrawContext {
  constructor() { this.size = null; this.opaque = true; this.respectScreenScale = false; this._path = null; }
  setFillColor(c) { this.#col(c); } setStrokeColor(c) { this.#col(c); }
  setLineWidth(n) { if (!isFinite(n)) throw new Error("bad line width"); }
  addPath(p) { if (!(p instanceof Path)) throw new Error("addPath needs a Path"); this._path = p; }
  fillPath() { if (!this._path) throw new Error("fillPath without addPath"); this._path = null; }
  strokePath() { if (!this._path) throw new Error("strokePath without addPath"); this._path = null; }
  fill(r) {} fillEllipse(r) {} strokeRect(r) {} strokeEllipse(r) {}
  setFont(f) { if (!(f instanceof Font)) throw new Error("setFont needs a Font"); }
  setTextColor(c) { this.#col(c); }
  setTextAlignedCenter() {} setTextAlignedLeft() {} setTextAlignedRight() {}
  drawText(t, p) { if (typeof t !== "string") throw new Error("drawText needs string"); }
  drawTextInRect(t, r) { if (typeof t !== "string") throw new Error("drawTextInRect needs string"); if (!(r instanceof Rect)) throw new Error("needs Rect"); }
  drawImageAtPoint() {} drawImageInRect() {}
  getImage() { if (!(this.size instanceof Size)) throw new Error("DrawContext.size not set"); return new Image_(); }
  #col(c) { if (!(c instanceof Color)) throw new Error("expected a Color"); }
}
class SFSymbol {
  static named(name) {
    // real API returns null for unknown symbols — exercise both paths
    if (typeof name !== "string" || !name) return null;
    if (globalThis.__SF_NULL) return null;
    const s = new SFSymbol(); s.image = new Image_(); return s;
  }
  applyFont(f) { if (!(f instanceof Font)) throw new Error("applyFont needs Font"); }
}
const files = new Map();
const fmStub = {
  cacheDirectory: () => "/cache",
  libraryDirectory: () => "/lib",
  documentsDirectory: () => "/docs",
  joinPath: (a, b) => `${a}/${b}`,
  fileExists: (p) => files.has(p),
  readString: (p) => { if (!files.has(p)) throw new Error("no file"); return files.get(p); },
  writeString: (p, s) => { files.set(p, s); },
};
const FileManager = { local: () => fmStub, iCloud: () => fmStub };
class Request {
  constructor(url) { this.url = url; this.timeoutInterval = 0; }
  async loadJSON() {
    if (globalThis.__NET_FAIL) throw new Error("offline (stubbed)");
    return JSON.parse(JSON.stringify(globalThis.__FIXTURE));
  }
  async loadString() { return ""; }
}
const Script = { setWidget: (w) => { globalThis.__LAST_WIDGET = w; }, complete: () => {}, name: () => "bling" };
const Device = { isUsingDarkAppearance: () => !!globalThis.__DARK };

Object.assign(globalThis, {
  Color, Font, Point, Size, Rect, Image: Image_, LinearGradient, ListWidget,
  Path, DrawContext, SFSymbol, FileManager, Request, Script, Device,
});

// ── fixtures ───────────────────────────────────────────────────────────────
const FULL = {
  updated: "2026-07-01", generated_at: "23:05", runway_months: 16.2,
  liquid: 163000, burn: 10063, income_target: 10647,
  buys: ["RUSTA.ST", "NVDA"], watch_count: 12, swing_count: 149,
  sell_alerts: ["TAKE PROFIT KOG.OL"],
  holdings: [
    { ticker: "KOG.OL", price: 512, cost: 400, stop: 360, target: 600, target_kind: "analyst", progress: 0.56, gain_pct: 28.0, day_pct: 1.4, stop_hit: false },
    { ticker: "NOD.OL", price: 91, cost: 120, stop: 95, target: 180, target_kind: null, progress: 0, gain_pct: -24.2, day_pct: -2.1, stop_hit: true },
    { ticker: "RUSTA.ST", price: 60, cost: 55, stop: null, target: 90, target_kind: "value", progress: 0.14, gain_pct: 9.1, day_pct: 0.0, stop_hit: false },
    { ticker: "AAPL", price: 210, cost: null, stop: null, target: null, target_kind: null, progress: null, gain_pct: null, day_pct: null, stop_hit: false },
  ],
  markets: [
    { label: "OSEBX", day_pct: 0.4, trend_up: true },
    { label: "SPX", day_pct: -0.8, trend_up: false },
    { label: "NOK", day_pct: 0.1, trend_up: true },
  ],
};
const EMPTY = { updated: "2026-07-01", generated_at: "23:05", runway_months: 16.2, liquid: 163000, burn: 10063, income_target: 10647, buys: [], watch_count: 12, swing_count: 149, sell_alerts: [], holdings: [], markets: [] };
const HOSTILE = { // wrong types + missing keys + junk entries everywhere
  runway_months: null, liquid: "163000", burn: null, income_target: undefined,
  buys: "RUSTA.ST", watch_count: "12", swing_count: null, sell_alerts: [null, 42],
  holdings: [null, "junk", {}, { ticker: "X", price: "NaN", cost: NaN, stop: Infinity, target: -5, progress: 7, gain_pct: "up", day_pct: {}, stop_hit: "yes" }],
  markets: [null, {}, { label: 3, day_pct: "x", trend_up: "maybe" }],
};
const MINIMAL = {};

// ── matrix ─────────────────────────────────────────────────────────────────
const core = require("/root/Project-Bling-Empire/v2/widgets/bling-widget-core.js");
const families = ["small", "medium", "large", "extraLarge", "accessoryRectangular", "accessoryCircular", "accessoryInline", null];
const params = [null, "", "brief", "runway", "positions", "positions:5", "positions:0", "positions:99", "signals", "pulse",
  "brief,nopulse", "brief,nopulse,nofooter,nospark", "runway,plain", "positions,max:2", "positions:2,plain",
  "dark", "light", "  Signals , NOPULSE ", "garbage", "unknown:zzz,,,:::", "max:abc", "brief,positions:3,dark"];
const scenarios = [
  { name: "full", fixture: FULL, netFail: false },
  { name: "empty", fixture: EMPTY, netFail: false },
  { name: "hostile", fixture: HOSTILE, netFail: false },
  { name: "minimal{}", fixture: MINIMAL, netFail: false },
  { name: "offline+cache", fixture: FULL, netFail: true, preCache: FULL },
  { name: "offline-nocache", fixture: null, netFail: true, preCache: null },
];

let runs = 0, failures = [];
for (const sc of scenarios) {
  for (const dark of [false, true]) {
    for (const fam of families) {
      for (const p of params) {
        files.clear();
        if (sc.preCache) files.set("/cache/bling-widget.json", JSON.stringify(sc.preCache));
        globalThis.__NET_FAIL = sc.netFail;
        globalThis.__FIXTURE = sc.fixture;
        globalThis.__DARK = dark;
        globalThis.__SF_NULL = sc.name === "hostile"; // hostile also gets null SFSymbols
        globalThis.__LAST_WIDGET = null;
        globalThis.config = { widgetFamily: fam, runsInApp: false, runsInWidget: true };
        globalThis.args = { widgetParameter: p };
        runs++;
        try {
          await core({ URL_BASE: "http://test.local", TOKEN: "tok" });
          const w = globalThis.__LAST_WIDGET;
          if (!(w instanceof ListWidget)) throw new Error("Script.setWidget never called with a ListWidget");
          const texts = [];
          (function walk(n) { for (const it of n.items || []) { if (it.text !== undefined) texts.push(it.text); walk(it); } })(w);
          if (!texts.length && !w.items.some((i) => i instanceof WidgetImage || i instanceof WidgetStack))
            throw new Error("widget rendered completely empty");
          if (texts.some((t) => t.startsWith("Bling render error")))
            throw new Error(`internal render error surfaced: ${texts.find((t) => t.startsWith("Bling render error"))}`);
        } catch (e) {
          failures.push(`[${sc.name}|dark=${dark}|${fam}|param=${JSON.stringify(p)}] ${e.message}`);
        }
      }
    }
  }
}

// runsInApp path once (presentLarge)
globalThis.__NET_FAIL = false; globalThis.__FIXTURE = FULL; globalThis.__DARK = false; globalThis.__SF_NULL = false;
globalThis.config = { widgetFamily: "large", runsInApp: true, runsInWidget: false };
globalThis.args = { widgetParameter: "brief" };
runs++;
try { await core({ URL_BASE: "http://test.local", TOKEN: "tok" }); } catch (e) { failures.push(`[runsInApp] ${e.message}`); }

// version stamp check
const src = files.get("/cache/bling-widget.json"); // just ensures cache flow ran
import { readFileSync } from "node:fs";
const coreSrc = readFileSync("/root/Project-Bling-Empire/v2/widgets/bling-widget-core.js", "utf8");
if (!coreSrc.includes('CORE_VERSION = "3.1"')) failures.push("CORE_VERSION is not 3.1");
if (!coreSrc.includes("module.exports")) failures.push("loader contract broken: no module.exports");
if (!src) failures.push("offline cache was never written on a successful fetch");

console.log(`ran ${runs} combos (${scenarios.length} payload scenarios × 2 appearances × ${families.length} families × ${params.length} parameters + app run)`);
if (failures.length) {
  console.error(`FAILURES: ${failures.length}`);
  for (const f of failures.slice(0, 40)) console.error("  " + f);
  process.exit(1);
}
console.log("ALL GREEN — no throws, widget always set, no surfaced render errors");

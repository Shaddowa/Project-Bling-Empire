// Bling Empire — widget LOADER (Scriptable). Paste this ONCE, never again.
//
// It downloads the real widget code from your dashboard on every run, so
// improvements ship from the VPS to your home screen automatically (~10 min).
// If the server is unreachable it runs the last downloaded copy.
//
// Setup: paste TOKEN from v2/.dashboard-creds. Widget Parameter still picks
// the view: brief / runway / positions / signals.

const URL_BASE = "http://187.127.113.131:3400";
const TOKEN = "PASTE_WIDGET_TOKEN_HERE";

const fm = FileManager.local();
const corePath = fm.joinPath(fm.libraryDirectory(), "bling-widget-core.js");

try {
  const req = new Request(`${URL_BASE}/api/widget-script?token=${TOKEN}`);
  req.timeoutInterval = 15;
  const code = await req.loadString();
  if (code.includes("module.exports")) fm.writeString(corePath, code);
} catch (e) { /* offline: run the cached core below */ }

if (!fm.fileExists(corePath)) {
  const w = new ListWidget();
  w.addText("Bling: first run needs the server reachable once.");
  Script.setWidget(w); Script.complete();
} else {
  const core = importModule(corePath);
  await core({ URL_BASE, TOKEN });
}

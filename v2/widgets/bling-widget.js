// Bling Empire — iOS home-screen widget (Scriptable app)
//
// Setup (2 min): App Store -> "Scriptable" -> new script -> paste this ->
// fill URL + TOKEN from v2/.dashboard-creds -> long-press home screen ->
// add Scriptable widget (small or medium) -> choose this script.
//
// Shows: runway, burn, today's BUYs and sell alerts. Updates ~every 15 min.

const URL_BASE = "http://187.127.113.131:3400";
const TOKEN = "PASTE_WIDGET_TOKEN_HERE";

const req = new Request(`${URL_BASE}/api/widget?token=${TOKEN}`);
const data = await req.loadJSON();

const w = new ListWidget();
w.backgroundColor = new Color("#f2ece0");
w.setPadding(14, 14, 12, 14);
w.url = URL_BASE;

const ink = new Color("#171512"), muted = new Color("#6b6358");
const good = new Color("#0e9f6e"), bad = new Color("#c2410c"), accent = new Color("#14582f");

const title = w.addText("💰 Bling");
title.font = Font.boldSystemFont(11);
title.textColor = muted;
w.addSpacer(4);

const runway = w.addText(data.runway_months === null ? "∞" : `${data.runway_months} mo`);
runway.font = Font.boldSystemFont(26);
runway.textColor = ink;
const sub = w.addText(`runway · burn ${Math.round(data.burn / 1000)}k/mo`);
sub.font = Font.systemFont(10);
sub.textColor = muted;
w.addSpacer(6);

if (data.sell_alerts.length) {
  const sell = w.addText(`🔴 ${data.sell_alerts.join(" ")}`);
  sell.font = Font.boldSystemFont(11);
  sell.textColor = bad;
}
if (data.buys.length) {
  const buy = w.addText(`🟢 BUY ${data.buys.join(" ")}`);
  buy.font = Font.boldSystemFont(11);
  buy.textColor = good;
  buy.lineLimit = 2;
} else if (!data.sell_alerts.length) {
  const calm = w.addText(`no actions · ${data.watch_count} on watch`);
  calm.font = Font.systemFont(11);
  calm.textColor = accent;
}
w.addSpacer(4);
const stamp = w.addText(`as of ${data.updated}`);
stamp.font = Font.systemFont(8);
stamp.textColor = muted;

Script.setWidget(w);
Script.complete();
if (config.runsInApp) w.presentMedium();

"""Render the analyzed universe into a ranked CSV and a readable HTML report."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from .engine import TickerReport

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
ACTION_ORDER = {"BUY": 0, "WATCH": 1, "FAIR": 2, "AVOID": 3}
ACTION_COLORS = {"BUY": "#1e7d32", "WATCH": "#e09b00", "FAIR": "#6b7280", "AVOID": "#b91c1c"}


def _pct(value: Optional[float]) -> Optional[float]:
    return round(100.0 * value, 1) if value is not None else None


def reports_to_frame(reports: list[TickerReport]) -> pd.DataFrame:
    rows = []
    for r in reports:
        rows.append({
            "ACTION": r.action,
            "TICKER": r.ticker,
            "COMPANY": r.name,
            "SECTOR": r.sector,
            "PRICE": r.valuation.price,
            "CURRENCY": r.currency,
            "QUALITY SCORE": r.quality.score,
            "CRITERIA PASSED": f"{r.quality.passed}/{r.quality.total}" if r.quality.total else "",
            "GROWTH EST %": _pct(r.valuation.growth_estimate),
            "STICKER PRICE": round(r.valuation.sticker_price, 2) if r.valuation.sticker_price else None,
            "MOS PRICE": round(r.valuation.mos_price, 2) if r.valuation.mos_price else None,
            "DISCOUNT TO STICKER %": _pct(r.valuation.discount_to_sticker),
            "PAYBACK YEARS": r.valuation.payback_years,
            "VALUATION": r.valuation.verdict,
            "SIGNAL": r.signal.signal,
            "MACD": r.signal.macd_bullish,
            "STOCH": r.signal.stochastic_bullish,
            "SMA10": r.signal.sma10_bullish,
            "ABOVE 200SMA": r.signal.above_200_sma,
            "SIGNAL AGE (DAYS)": r.signal.days_in_current_signal,
            "DIVIDEND SCORE": r.dividends.score,
            "SELL GUIDANCE": r.sell_guidance,
            "ERROR": r.error,
        })
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["_action_rank"] = frame["ACTION"].map(ACTION_ORDER).fillna(9)
    frame = frame.sort_values(
        by=["_action_rank", "QUALITY SCORE", "DISCOUNT TO STICKER %"],
        ascending=[True, False, False],
    ).drop(columns="_action_rank").reset_index(drop=True)
    return frame


def write_reports(frame: pd.DataFrame, universe_label: str,
                  output_dir: Optional[Path] = None) -> tuple[Path, Path]:
    out = (output_dir or OUTPUT_DIR) / date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / f"signals_{universe_label}.csv"
    html_path = out / f"signals_{universe_label}.html"
    frame.to_csv(csv_path, index=False)
    html_path.write_text(_render_html(frame, universe_label))
    return csv_path, html_path


def _render_html(frame: pd.DataFrame, universe_label: str) -> str:
    def cell(value) -> str:
        if value is None or value != value:  # NaN
            return "<td></td>"
        if isinstance(value, bool) or value in (True, False):
            return f'<td class="{"yes" if value else "no"}">{"✓" if value else "✗"}</td>'
        return f"<td>{value}</td>"

    header = "".join(f"<th>{c}</th>" for c in frame.columns)
    body_rows = []
    for _, row in frame.iterrows():
        color = ACTION_COLORS.get(row["ACTION"], "#6b7280")
        cells = [f'<td style="color:{color};font-weight:700">{row["ACTION"]}</td>']
        cells += [cell(v) for v in row.iloc[1:]]
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    counts = frame["ACTION"].value_counts().to_dict() if not frame.empty else {}
    summary = " · ".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda i: ACTION_ORDER.get(i[0], 9)))
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Bling Empire signals — {universe_label} — {date.today()}</title>
<style>
 body {{ font-family: -apple-system, Segoe UI, sans-serif; margin: 2rem; color: #111; }}
 h1 {{ font-size: 1.3rem; }} .sub {{ color: #555; margin-bottom: 1rem; }}
 table {{ border-collapse: collapse; font-size: 0.82rem; width: 100%; }}
 th {{ position: sticky; top: 0; background: #111; color: #fff; padding: 6px 8px; text-align: left; cursor: default; }}
 td {{ padding: 5px 8px; border-bottom: 1px solid #e5e7eb; white-space: nowrap; }}
 tr:hover {{ background: #f3f4f6; }}
 .yes {{ color: #1e7d32; }} .no {{ color: #b91c1c; }}
</style></head><body>
<h1>💰 Project Bling Empire — {universe_label} signals — {date.today()}</h1>
<div class="sub">{summary}<br>
BUY = quality ≥ 60 + price below margin of safety + all three timing tools bullish ·
WATCH = right company &amp; price, wrong timing ·
FAIR = right company, wrong price ·
AVOID = failed the quality screen.<br>
Not financial advice — a decision-support screen. Verify before trading.</div>
<table><thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>
</body></html>"""

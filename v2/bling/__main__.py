"""Command-line entry point.

    python -m bling run --universe oslo sp500      # full screen -> CSV + HTML
    python -m bling analyze EQNR.OL                # one-ticker deep dive
    python -m bling backtest --universe oslo       # validate the timing rules
"""
from __future__ import annotations

import argparse
from datetime import timedelta

from .backtest import backtest_portfolio, format_metrics
from .engine import QUALITY_THRESHOLD, analyze_ticker, analyze_universe
from .report import reports_to_frame, write_reports
from .universe import available_universes, load_universe


def cmd_run(args: argparse.Namespace) -> None:
    for name in args.universe:
        tickers = load_universe(name)
        if args.limit:
            tickers = tickers[: args.limit]
        print(f"Screening {len(tickers)} tickers from {name} ...")
        reports = analyze_universe(tickers, max_age=timedelta(days=args.max_age_days))
        frame = reports_to_frame(reports)
        csv_path, html_path = write_reports(frame, name)
        buys = frame[frame["ACTION"] == "BUY"]["TICKER"].tolist()
        watch = frame[frame["ACTION"] == "WATCH"]["TICKER"].tolist()
        print(f"  BUY:   {', '.join(buys) or '—'}")
        print(f"  WATCH: {', '.join(watch) or '—'}")
        print(f"  report: {html_path}\n  csv:    {csv_path}")


def cmd_analyze(args: argparse.Namespace) -> None:
    r = analyze_ticker(args.ticker, max_age=timedelta(days=args.max_age_days))
    v, s = r.valuation, r.signal
    print(f"\n{r.ticker} — {r.name or '?'} ({r.sector or '?'}) — {v.price} {r.currency or ''}")
    if r.error:
        print(f"  data error: {r.error}")
        return
    print(f"\nACTION: {r.action}    (holders: {r.sell_guidance})")
    print(f"\nQuality score {r.quality.score} ({r.quality.passed}/{r.quality.total} criteria, "
          f"{r.quality.years_of_data} years of statements)")
    for name, verdict in r.quality.verdicts.items():
        metric = r.quality.metrics.get(name)
        if metric is None:
            shown = ""
        elif name == "debt_payoff":
            shown = f"{metric}y of FCF"
        elif name == "fcf_increasing":
            shown = f"latest {metric:,.0f}"
        else:
            shown = f"{metric:+.1%}"
        print(f"  {verdict.value:<8} {name:<30} {shown}")
    growth = f"{v.growth_estimate:+.1%}" if v.growth_estimate is not None else "n/a"
    sticker = f"{v.sticker_price:.2f}" if v.sticker_price else "n/a"
    mos = f"{v.mos_price:.2f}" if v.mos_price else "n/a"
    ten_cap = f"{v.ten_cap_price:.2f}" if v.ten_cap_price else "n/a"
    print(f"\nValuation: {v.verdict}  growth est {growth}  sticker {sticker}  "
          f"MOS {mos}  ten-cap {ten_cap}  payback {v.payback_years or 'n/a'}y")
    print(f"Timing: {s.signal} (for {s.days_in_current_signal} days)  "
          f"MACD {'✓' if s.macd_bullish else '✗'}  Stoch {'✓' if s.stochastic_bullish else '✗'}  "
          f"SMA10 {'✓' if s.sma10_bullish else '✗'}  200SMA trend {'up' if s.above_200_sma else 'down'}")
    print(f"Dividend score: {r.dividends.score}/10")


def cmd_backtest(args: argparse.Namespace) -> None:
    if args.tickers:
        tickers = args.tickers
    else:
        tickers = []
        for name in args.universe:
            universe = load_universe(name)
            tickers += universe[: args.limit] if args.limit else universe
    if args.qualified_only:
        print(f"Screening {len(tickers)} tickers for quality >= {QUALITY_THRESHOLD} first ...")
        reports = analyze_universe(tickers)
        tickers = [r.ticker for r in reports if r.quality.score >= QUALITY_THRESHOLD]
        print(f"  {len(tickers)} qualified: {', '.join(tickers) or '—'}")
    if not tickers:
        print("nothing to backtest")
        return
    print(f"Backtesting three-tool timing on {len(tickers)} tickers (10y daily) ...")
    result = backtest_portfolio(tickers)
    if result is None:
        print("no tickers had enough price history")
        return
    print()
    print(format_metrics(result.strategy))
    print(format_metrics(result.buy_hold))
    if args.per_ticker:
        print()
        for row in result.per_ticker:
            print(format_metrics(row["strategy"]))
            print(format_metrics(row["buy_hold"]))


def main() -> None:
    parser = argparse.ArgumentParser(prog="bling", description="Project Bling Empire v2 — stock signal engine")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="screen universes and write signal reports")
    run.add_argument("--universe", nargs="+", default=["oslo"], choices=available_universes())
    run.add_argument("--limit", type=int, default=None, help="only the first N tickers (for testing)")
    run.add_argument("--max-age-days", type=int, default=1, help="reuse cached data younger than this")
    run.set_defaults(func=cmd_run)

    analyze = sub.add_parser("analyze", help="deep dive on a single ticker")
    analyze.add_argument("ticker")
    analyze.add_argument("--max-age-days", type=int, default=1)
    analyze.set_defaults(func=cmd_analyze)

    backtest = sub.add_parser("backtest", help="backtest the timing rules")
    backtest.add_argument("--universe", nargs="+", default=["oslo"], choices=available_universes())
    backtest.add_argument("--tickers", nargs="+", default=None, help="explicit ticker list instead of a universe")
    backtest.add_argument("--limit", type=int, default=None)
    backtest.add_argument("--qualified-only", action="store_true",
                          help="only backtest stocks passing the quality screen")
    backtest.add_argument("--per-ticker", action="store_true")
    backtest.set_defaults(func=cmd_backtest)

    refresh = sub.add_parser("refresh-universe", help="regenerate ticker lists from live sources")
    refresh.set_defaults(func=lambda args: __import__(
        "bling.universe_refresh", fromlist=["refresh_all"]).refresh_all())

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

"""
main.py - AI Financial Decision Engine

Usage:
    python main.py train                     Generate dataset, train all models
    python main.py evaluate                  Evaluate saved models, generate reports
    python main.py predict                   Interactive prediction from user input
    python main.py run                       Full pipeline: train + evaluate
    python main.py rules                     Pure if-else engine (zero ML dependencies)
    python main.py api                       Start FastAPI server (http://localhost:8000)

    -- New real-time features --
    python main.py stock   TICKER            Price + fundamentals for a stock
    python main.py signals TICKER            Buy/Sell signals (RSI, MACD, MA...)
    python main.py score   TICKER            Composite score (0-100) + grade
    python main.py rank    TICKER [TICKER..] Rank a list of stocks by score
    python main.py sentiment TICKER          News sentiment analysis
    python main.py rebalance                 Portfolio rebalancing plan (interactive)
    python main.py monitor TICKER [TICKER..] Start 24/7 watchdog (Ctrl-C to stop)
    python main.py alerts list               List active alerts
    python main.py alerts add                Add a new alert (interactive)
    python main.py alerts delete ID          Delete alert by ID

    -- SIP & Fund features --
    python main.py sip-project               Project corpus: INR X/mo for Y years = INR Z
    python main.py sip-goal                  SIP needed / duration to reach a goal amount
    python main.py sip-split                 Split SIP across specific funds with percentages
    python main.py sip-plan                  Full SIP plan: split + projection + goal analysis
    python main.py fund-compare              Compare Fund A vs Fund B for your goal
    python main.py fund-list                 Browse all available funds in the database
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


BANNER = """
============================================================
   AI FINANCIAL DECISION ENGINE
   PART (Partial Decision Trees)  |  Rule Engine
============================================================
"""


# ── Existing commands ──────────────────────────────────────────────────────────

def cmd_train(args):
    from financial_engine.data_generation import generate_dataset
    from financial_engine.model_training import run_training

    print(BANNER)
    print("[STEP 1] Generating synthetic dataset...")
    print("-" * 50)
    generate_dataset(output_path=args.dataset)
    print()

    print("[STEP 2] Training all models...")
    print("-" * 50)
    run_training(csv_path=args.dataset, model_dir=args.model_dir)
    print()
    print("Training complete. Models saved to:", args.model_dir)


def cmd_evaluate(args):
    from financial_engine.model_training import load_models, load_and_encode
    from financial_engine.evaluation import run_evaluation

    print(BANNER)
    print("[EVALUATE] Loading models and test data...")
    print("-" * 50)

    models, data_bundle = load_models(args.model_dir)
    data = load_and_encode(args.dataset)
    data.update(data_bundle)
    run_evaluation(models, data, output_dir=args.output_dir)
    print("Output files saved to:", args.output_dir)


def cmd_predict(args):
    from financial_engine.predictor import run_prediction
    print(BANNER)
    run_prediction(model_dir=args.model_dir)


def cmd_rules(args):
    from financial_engine.rule_engine import run_rule_engine
    run_rule_engine()


def cmd_api(args):
    import uvicorn
    print(BANNER)
    print(f"Starting FastAPI server on http://{args.host}:{args.port}")
    print(f"Docs:  http://{args.host}:{args.port}/docs")
    print("-" * 50)
    uvicorn.run(
        "financial_engine.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def cmd_run(args):
    cmd_train(args)
    print()
    cmd_evaluate(args)


# ── New real-time commands ─────────────────────────────────────────────────────

def cmd_stock(args):
    """Fetch and display current price + fundamentals for one ticker."""
    from financial_engine.stock_data_fetcher import get_stock_price, get_fundamentals
    import json

    ticker = args.ticker
    print(f"\n{'='*60}")
    print(f"  STOCK DATA: {ticker}")
    print(f"{'='*60}")

    price = get_stock_price(ticker)
    fund  = get_fundamentals(ticker)

    if "error" in price:
        print(f"Price error: {price['error']}")
    else:
        print(f"\n  Name         : {price.get('name')}")
        print(f"  Price        : {price.get('currency', '')} {price.get('current_price')}")
        print(f"  Change       : {price.get('change'):+.2f}  ({price.get('change_pct'):+.2f}%)")
        print(f"  Day H/L      : {price.get('day_high')} / {price.get('day_low')}")
        print(f"  52w H/L      : {price.get('52w_high')} / {price.get('52w_low')}")
        print(f"  Volume       : {price.get('volume'):,}")

    if "error" not in fund:
        print(f"\n  --- Fundamentals ---")
        print(f"  Sector       : {fund.get('sector')}")
        print(f"  Market Cap   : {fund.get('market_cap'):,}" if fund.get('market_cap') else "  Market Cap   : N/A")
        print(f"  PE Ratio     : {fund.get('pe_ratio')}")
        print(f"  EPS (TTM)    : {fund.get('eps_ttm')}")
        print(f"  EPS Forward  : {fund.get('eps_forward')}")
        print(f"  Debt/Equity  : {fund.get('debt_to_equity')}")
        roe_str = f"{fund.get('roe')*100:.1f}%" if fund.get('roe') else "N/A"
        pm_str  = f"{fund.get('profit_margin')*100:.1f}%" if fund.get('profit_margin') else "N/A"
        dy_str  = f"{fund.get('dividend_yield')*100:.2f}%" if fund.get('dividend_yield') else "N/A"
        print(f"  ROE          : {roe_str}")
        print(f"  Profit Margin: {pm_str}")
        print(f"  Div Yield    : {dy_str}")
        print(f"  Analyst Tgt  : {fund.get('target_price')}")
        print(f"  Beta         : {fund.get('beta')}")
    print()


def cmd_signals(args):
    """Generate and display Buy/Sell signals for a ticker."""
    from financial_engine.signal_engine import generate_signals

    ticker = args.ticker
    period = getattr(args, "period", "6mo")
    print(f"\n{'='*60}")
    print(f"  SIGNALS: {ticker}  (period={period})")
    print(f"{'='*60}")

    result = generate_signals(ticker, period=period)

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    print(f"\n  Signal   : {result['signal']} ({result['strength']})")
    print(f"  Score    : {result['score']:+.3f}  (-1.0=strong sell ... +1.0=strong buy)")
    print(f"  Price    : {result.get('current_price')}")
    print(f"\n  --- Indicator Breakdown ---")

    ind = result.get("indicators", {})
    rsi_val = ind.get('rsi', {}).get('value')
    rsi_val_str = f"{rsi_val:.1f}" if rsi_val is not None else "N/A"
    print(f"  RSI              : {rsi_val_str}  -> {ind.get('rsi', {}).get('reason')}")
    print(f"  MACD histogram   : {ind.get('macd', {}).get('histogram')}  -> {ind.get('macd', {}).get('reason')}")
    print(f"  Moving Averages  : {ind.get('moving_averages', {}).get('reason')}")
    print(f"  Bollinger Bands  : {ind.get('bollinger_bands', {}).get('reason')}")
    print(f"  Stochastic       : {ind.get('stochastic', {}).get('reason')}")
    print(f"  Volume           : {ind.get('volume', {}).get('reason')}")
    print(f"  ADX (trend str.) : {ind.get('adx')}")
    print()


def cmd_score(args):
    """Composite score + grade for one ticker."""
    from financial_engine.stock_scorer import score_stock

    ticker = args.ticker
    print(f"\n{'='*60}")
    print(f"  STOCK SCORE: {ticker}")
    print(f"{'='*60}")

    result = score_stock(ticker)

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    print(f"\n  {result['name']}")
    print(f"  Score      : {result['score']}/100  [{result['grade']}]")
    print(f"  Action     : {result['recommendation']}")
    print(f"  Price      : {result.get('current_price')}  ({result.get('change_pct', 0):+.2f}%)")

    bd = result.get("breakdown", {})
    print(f"\n  --- Score Breakdown ---")
    print(f"  Fundamental  (30%) : {bd.get('fundamental', {}).get('score')}")
    print(f"  Technical    (40%) : {bd.get('technical',   {}).get('score')}  [{bd.get('technical', {}).get('signal')} {bd.get('technical', {}).get('strength')}]")
    print(f"  Valuation    (20%) : {bd.get('valuation',   {}).get('score')}")
    print(f"  Sentiment    (10%) : {bd.get('sentiment',   {}).get('score')}  [{bd.get('sentiment', {}).get('mood')}]")

    km = result.get("key_metrics", {})
    print(f"\n  --- Key Metrics ---")
    print(f"  PE Ratio    : {km.get('pe_ratio')}")
    print(f"  EPS (TTM)   : {km.get('eps_ttm')}")
    print(f"  Debt/Equity : {km.get('debt_to_equity')}")
    roe_str2 = f"{km.get('roe')*100:.1f}%" if km.get('roe') else "N/A"
    dy_str2  = f"{km.get('dividend_yield')*100:.2f}%" if km.get('dividend_yield') else "N/A"
    print(f"  ROE         : {roe_str2}")
    print(f"  Div Yield   : {dy_str2}")
    print(f"  Target Price: {km.get('target_price')}")
    print()


def cmd_rank(args):
    """Rank multiple tickers by composite score."""
    from financial_engine.stock_scorer import rank_stocks

    tickers = args.tickers
    print(f"\n{'='*60}")
    print(f"  STOCK RANKING  ({len(tickers)} tickers)")
    print(f"{'='*60}\n")
    print(f"  {'#':<3} {'Ticker':<14} {'Score':>6} {'Grade':<5} {'Rec':<12} {'Price':>10}  Signal")
    print(f"  {'-'*70}")

    results = rank_stocks(tickers)
    for r in results:
        rec  = r.get("recommendation", "N/A")
        sig  = r.get("breakdown", {}).get("technical", {}).get("signal", "")
        print(
            f"  {r['rank']:<3} {r['ticker']:<14} {r['score']:>6.1f} {r.get('grade','?'):<5} "
            f"{rec:<12} {str(r.get('current_price', 'N/A')):>10}  {sig}"
        )
    print()


def cmd_sentiment(args):
    """News sentiment for a ticker."""
    from financial_engine.sentiment_analyzer import get_stock_sentiment

    ticker = args.ticker
    print(f"\n{'='*60}")
    print(f"  SENTIMENT: {ticker}")
    print(f"{'='*60}")

    result = get_stock_sentiment(ticker)
    print(f"\n  Mood     : {result['mood']}")
    print(f"  Score    : {result['score']:+.3f}")
    print(f"  Articles : {result['num_articles']}  "
          f"(Bullish: {result.get('bullish_count',0)}, "
          f"Bearish: {result.get('bearish_count',0)}, "
          f"Neutral: {result.get('neutral_count',0)})")

    arts = result.get("article_sentiments", [])
    if arts:
        print(f"\n  Top Headlines:")
        for a in arts:
            sign = "+" if a["score"] > 0 else ("-" if a["score"] < 0 else " ")
            print(f"    [{sign}{abs(a['score']):.2f}] {a['title'][:70]}")
    print()


def cmd_rebalance(args):
    """Interactive portfolio rebalancing plan."""
    from financial_engine.rebalancing_engine import generate_rebalancing_plan

    print(BANNER)
    print("  PORTFOLIO REBALANCING")
    print("  Enter holdings (blank ticker to finish):\n")

    holdings = []
    while True:
        ticker = input("  Ticker (e.g. RELIANCE.NS) : ").strip()
        if not ticker:
            break
        try:
            qty    = float(input(f"  Quantity of {ticker}        : ").strip())
            price  = float(input(f"  Current price of {ticker}   : ").strip())
        except ValueError:
            print("  Invalid input, skipping.")
            continue
        cat = input(f"  Category (large_cap_equity/mid_cap_equity/debt_funds/liquid_funds/gold/international) [leave blank to auto-detect]: ").strip() or None
        holdings.append({"ticker": ticker, "quantity": qty, "current_price": price, "category": cat})

    risk = input("\n  Risk level (low/medium/high) [medium]: ").strip() or "medium"

    plan = generate_rebalancing_plan(holdings, risk_level=risk)
    if "error" in plan:
        print(f"\n  Error: {plan['error']}")
        return

    print(f"\n{'='*60}")
    print(f"  Portfolio Value  : INR {plan['total_portfolio_value']:,.2f}")
    print(f"  Max Drift        : {plan['max_drift_pct']}%")
    print(f"  Rebalancing      : {'NEEDED' if plan['needs_rebalancing'] else 'NOT NEEDED'}")
    print(f"{'='*60}")

    print("\n  Drift Analysis:")
    for cat, info in plan["drift_analysis"].items():
        act = f"  -> {info['action']}" if info["action"] != "OK" else ""
        print(f"    {cat:<25} Current: {info['current_pct']:>5.1f}%  Target: {info['target_pct']:>5.1f}%  Drift: {info['drift_pct']:>+5.1f}%{act}")

    if plan["sell_orders"]:
        print("\n  SELL ORDERS:")
        for o in plan["sell_orders"]:
            print(f"    SELL {o['quantity']} x {o['ticker']} @ {o['current_price']:.2f} = INR {o['estimated_value']:,.0f}  [{o['reason']}]")

    if plan["buy_orders"]:
        print("\n  BUY ORDERS:")
        for o in plan["buy_orders"]:
            print(f"    BUY INR {o['target_amount']:,.0f} in {o['category']}  [{o['reason']}]")
            print(f"      Suggestions: {', '.join(o['suggested_instruments'][:2])}")

    print("\n  Execution Notes:")
    for note in plan["execution_notes"]:
        print(f"    - {note}")
    print()


def cmd_monitor(args):
    """Start 24/7 watchdog for a list of tickers (Ctrl-C to stop)."""
    from financial_engine.watchdog import start_watchdog, stop_watchdog

    tickers = args.tickers
    print(BANNER)
    print(f"  Starting watchdog for: {', '.join(tickers)}")
    print(f"  Price check   : every {args.price_interval}s")
    print(f"  Technical     : every {args.tech_interval}s")
    print(f"  News          : every {args.news_interval}s")
    print("  Press Ctrl-C to stop.\n")

    dog = start_watchdog(
        tickers=tickers,
        check_interval_prices=args.price_interval,
        check_interval_technicals=args.tech_interval,
        check_interval_portfolio=args.portfolio_interval,
        check_interval_news=args.news_interval,
    )

    try:
        import time
        while True:
            time.sleep(10)
            status = dog.get_status()
            print(f"  [watchdog] Alerts so far: {status['alert_count']} | "
                  f"Last checks: {status['last_check']}")
    except KeyboardInterrupt:
        print("\n  Stopping watchdog...")
        stop_watchdog()
        print("  Watchdog stopped.")


def cmd_alerts(args):
    """Manage alerts (list / add / delete)."""
    from financial_engine.alert_manager import (
        list_alerts, create_alert, delete_alert, ALERT_TYPES
    )

    sub = args.alerts_cmd

    if sub == "list":
        alerts = list_alerts(active_only=not getattr(args, "all", False))
        if not alerts:
            print("  No active alerts.")
            return
        print(f"\n  {'ID':<10} {'Type':<18} {'Ticker':<14} {'Target':>10}  {'Dir':<6}  Triggered")
        print(f"  {'-'*70}")
        for a in alerts:
            print(f"  {a['id']:<10} {a['type']:<18} {str(a.get('ticker','')):<14} "
                  f"{str(a.get('target_value',''))[:10]:>10}  {a.get('direction',''):<6}  "
                  f"{'YES ('+str(a['trigger_count'])+')' if a.get('triggered') else 'No'}")
        print()

    elif sub == "add":
        print("\n  Available types:", ", ".join(ALERT_TYPES.keys()))
        atype  = input("  Alert type : ").strip()
        ticker = input("  Ticker     : ").strip() or None
        try:
            target = float(input("  Target value (e.g. price level or RSI threshold): ").strip())
        except ValueError:
            target = None
        direction = input("  Direction (above/below) [above]: ").strip() or "above"
        email     = input("  Notify email (blank to skip)   : ").strip() or None
        msg       = input("  Custom message (optional)      : ").strip()

        alert = create_alert(atype, ticker=ticker, target_value=target,
                             direction=direction, notify_email=email, message=msg)
        print(f"\n  [OK] Alert created: ID={alert['id']}  {atype} @ {target}")

    elif sub == "delete":
        alert_id = args.alert_id
        if delete_alert(alert_id):
            print(f"  [OK] Alert {alert_id} deleted.")
        else:
            print(f"  [ERR] Alert {alert_id} not found.")


# ── SIP & Fund command functions ───────────────────────────────────────────────

def cmd_sip_project(args):
    """Project corpus from a SIP: INR X/mo for Y years at Z% = INR W"""
    from financial_engine.sip_calculator import project_corpus, compare_flat_vs_stepup

    sip    = args.sip
    years  = args.years
    cagr   = args.cagr
    stepup = args.step_up
    exist  = args.existing

    S = "=" * 62
    print(S); print("  SIP CORPUS PROJECTION"); print(S)
    print(f"  Monthly SIP     : INR {sip:,.0f}")
    print(f"  Horizon         : {years} years")
    print(f"  CAGR assumption : {cagr}%")
    if exist:
        print(f"  Existing corpus : INR {exist:,.0f}")

    flat = project_corpus(sip, years, cagr=cagr, step_up_pct=0.0, existing_corpus=exist)
    print()
    print("  [Flat SIP]")
    print(f"  Total invested  : INR {flat['total_invested']:,.0f}")
    print(f"  Final corpus    : INR {flat['final_corpus']:,.0f}")
    print(f"  Wealth gain     : INR {flat['wealth_gain']:,.0f}")
    print(f"  Multiplier      : {flat['wealth_multiplier']}x")

    if stepup > 0:
        cmp = compare_flat_vs_stepup(sip, years, cagr=cagr, step_up_pct=stepup)
        su  = cmp["step_up_sip"]
        print()
        print(f"  [Step-up SIP  +{stepup}%/yr]")
        print(f"  Total invested  : INR {su['total_invested']:,.0f}")
        print(f"  Final corpus    : INR {su['final_corpus']:,.0f}")
        print(f"  Wealth gain     : INR {su['wealth_gain']:,.0f}")
        print(f"  Extra vs flat   : INR {cmp['extra_corpus']:,.0f} more corpus")

    print()
    print("  Year-by-Year Table (flat SIP):")
    print(f"  {'Year':<5} {'Monthly SIP':>12} {'Invested':>14} {'Corpus':>16} {'Gain':>14}")
    print(f"  {'-'*65}")
    for row in flat["yearly_table"]:
        print(f"  {row['year']:<5} {row['monthly_sip']:>12,.0f} {row['total_invested']:>14,.0f} "
              f"{row['corpus']:>16,.0f} {row['wealth_gain']:>14,.0f}")
    print()


def cmd_sip_goal(args):
    """SIP needed to reach a goal / how long to reach it."""
    from financial_engine.sip_calculator import sip_needed_for_goal, months_to_goal

    target = args.target
    years  = args.years
    sip    = args.sip
    cagr   = args.cagr
    exist  = args.existing

    S = "=" * 62
    print(S); print("  SIP GOAL CALCULATOR"); print(S)
    print(f"  Goal Amount     : INR {target:,.0f}")
    print(f"  CAGR assumption : {cagr}%")
    if exist:
        print(f"  Existing corpus : INR {exist:,.0f}")

    if years:
        result = sip_needed_for_goal(target, years, cagr=cagr, existing_corpus=exist)
        print()
        print(f"  [How much SIP for {years} years?]")
        print(f"  Monthly SIP needed : INR {result['monthly_sip_needed']:,.0f}")
        print(f"  Total invested     : INR {result['total_invested']:,.0f}")
        print(f"  Wealth gain        : INR {result['wealth_gain']:,.0f}")
        if exist:
            print(f"  Existing grows to  : INR {result['existing_fv']:,.0f}")

    if sip:
        result2 = months_to_goal(target, sip, cagr=cagr, existing_corpus=exist)
        print()
        print(f"  [How long at INR {sip:,.0f}/mo?]")
        print(f"  Time to goal       : {result2['years_needed']} years {result2['extra_months']} months")
        print(f"  Total months       : {result2['months_needed']}")
        print(f"  Total invested     : INR {result2['total_invested']:,.0f}")
        print(f"  Wealth gain        : INR {result2['wealth_gain']:,.0f}")
    print()


def cmd_sip_split(args):
    """Split SIP across specific named funds with percentages."""
    from financial_engine.fund_allocator import allocate_sip

    sip     = args.sip
    risk    = args.risk
    goal    = args.goal
    years   = args.years
    low_cost = args.low_cost

    S = "=" * 62
    print(S); print("  SIP FUND ALLOCATION"); print(S)
    print(f"  Total SIP   : INR {sip:,.0f}/mo")
    print(f"  Risk Level  : {risk}")
    print(f"  Goal Type   : {goal}")
    print(f"  Horizon     : {years} years")

    plan = allocate_sip(sip, risk_level=risk, goal_type=goal,
                        horizon_years=years, prefer_low_cost=low_cost)

    print()
    print(f"  Blended CAGR : {plan['blended_return']}%")
    print(f"  Funds        : {plan['num_funds']}")
    print()
    print(f"  {'#':<3} {'Fund Name':<38} {'Category':<18} {'INR/mo':>8}  {'Pct':>5}  {'5yr%':>6}  {'ER%':>5}")
    print(f"  {'-'*90}")
    for i, a in enumerate(plan["allocations"], 1):
        print(f"  {i:<3} {a['fund_name'][:37]:<38} {a['category']:<18} "
              f"{a['sip_amount']:>8,.0f}  {a['percentage']:>4.0f}%  "
              f"{a['returns_5yr']:>5.1f}%  {a['expense_ratio']:>4.2f}%")

    print()
    print(f"  Total : INR {sum(a['sip_amount'] for a in plan['allocations']):,.0f}/mo")
    print()
    print("  Fund Details:")
    for a in plan["allocations"]:
        print(f"  - {a['fund_name']}")
        print(f"    House: {a['fund_house']}  |  Risk: {a['risk']}  |  Min SIP: INR {a['min_sip']}")
        print(f"    Best for: {a['best_for']}")
    print()


def cmd_sip_plan(args):
    """Full SIP plan: fund split + corpus projection + goal analysis."""
    from financial_engine.sip_advisor import full_sip_plan

    plan = full_sip_plan(
        monthly_sip     = args.sip,
        goal_type       = args.goal,
        goal_amount     = args.target,
        horizon_years   = args.years,
        risk_level      = args.risk,
        step_up_pct     = args.step_up,
        existing_corpus = args.existing,
        prefer_low_cost = args.low_cost,
    )

    S = "=" * 62
    inp = plan["input"]
    print(S); print("  COMPLETE SIP PLAN"); print(S)
    print(f"  Monthly SIP     : INR {inp['monthly_sip']:,.0f}/mo")
    print(f"  Goal            : {inp['goal_type']}  |  Horizon: {inp['horizon_years']} years")
    print(f"  Risk            : {inp['risk_level']}")
    print(f"  Step-up         : {inp['step_up_pct']}%/yr")
    if inp["existing_corpus"]:
        print(f"  Existing Corpus : INR {inp['existing_corpus']:,.0f}")
    if inp["goal_amount"]:
        print(f"  Target Amount   : INR {inp['goal_amount']:,.0f}")

    print()
    print(S); print("  [1] FUND ALLOCATION"); print(S)
    print(f"  {'Fund':<38} {'Category':<18} {'INR/mo':>8}  {'Pct':>5}  {'5yr%':>6}")
    print(f"  {'-'*82}")
    for a in plan["fund_allocation"]:
        print(f"  {a['fund_name'][:37]:<38} {a['category']:<18} "
              f"{a['sip_amount']:>8,.0f}  {a['percentage']:>4.0f}%  {a['returns_5yr']:>5.1f}%")
    print(f"  Blended CAGR: {plan['blended_cagr']}%")

    print()
    print(S); print("  [2] CORPUS PROJECTION"); print(S)
    fp = plan["flat_projection"]
    sp = plan["stepup_projection"]
    print(f"  Flat SIP    : INR {inp['monthly_sip']:,.0f}/mo  ->  INR {fp['final_corpus']:,.0f}  "
          f"(invested INR {fp['total_invested']:,.0f}, gain INR {fp['wealth_gain']:,.0f})")
    print(f"  Step-up SIP : +{inp['step_up_pct']}%/yr  ->  INR {sp['final_corpus']:,.0f}  "
          f"(invested INR {sp['total_invested']:,.0f}, gain INR {sp['wealth_gain']:,.0f})")
    cmp = plan["stepup_comparison"]
    print(f"  Step-up gives INR {cmp['extra_corpus']:,.0f} more corpus "
          f"by investing INR {cmp['extra_invested']:,.0f} more")

    print()
    print(S); print("  [3] FUND-LEVEL PROJECTIONS (with step-up)"); print(S)
    print(f"  {'Fund':<38} {'SIP/mo':>8}  {'5yr%':>6}  {'Corpus':>14}  {'Gain':>14}")
    print(f"  {'-'*84}")
    for p in plan["fund_level_projections"]:
        print(f"  {p['fund_name'][:37]:<38} {p['sip_amount']:>8,.0f}  "
              f"{p['returns_5yr']:>5.1f}%  {p['final_corpus']:>14,.0f}  {p['wealth_gain']:>14,.0f}")
    print(f"  Total projected corpus: INR {plan['total_projected_corpus']:,.0f}")

    ga = plan["goal_analysis"]
    if ga:
        print()
        print(S); print("  [4] GOAL ANALYSIS"); print(S)
        print(f"  Goal Amount           : INR {ga['goal_amount']:,.0f}")
        flat_status   = "REACHED" if ga['flat_reaches_goal']   else f"Short by INR {ga['flat_shortfall']:,.0f}"
        stepup_status = "REACHED" if ga['stepup_reaches_goal'] else f"Short by INR {ga['stepup_shortfall']:,.0f}"
        print(f"  Flat SIP corpus       : INR {ga['flat_final_corpus']:,.0f}  ({flat_status})")
        print(f"  Step-up corpus        : INR {ga['stepup_final_corpus']:,.0f}  ({stepup_status})")
        print(f"  SIP needed (on time)  : INR {ga['sip_needed']:,.0f}/mo  "
              f"(+INR {ga['extra_sip_needed']:,.0f} more)")
        print(f"  Duration (current SIP): {ga['years_at_current_sip']} yrs {ga['extra_months']} months")
        print(f"  Verdict               : {ga['verdict']}")
    print()


def cmd_fund_compare(args):
    """Compare multiple funds side-by-side for a goal."""
    from financial_engine.fund_comparator import compare_funds

    result = compare_funds(
        fund_queries    = args.funds,
        monthly_sip     = args.sip,
        years           = args.years,
        goal_amount     = args.target,
        existing_corpus = args.existing,
        step_up_pct     = args.step_up,
    )

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    S = "=" * 62
    print(S); print("  FUND COMPARISON"); print(S)
    print(f"  Monthly SIP  : INR {result['monthly_sip']:,.0f}/mo")
    print(f"  Horizon      : {result['years']} years")
    if result["goal_amount"]:
        print(f"  Goal Amount  : INR {result['goal_amount']:,.0f}")
    if result["step_up_pct"]:
        print(f"  Step-up      : {result['step_up_pct']}%/yr")
    if result["not_found"]:
        print(f"  Not found    : {', '.join(result['not_found'])}")

    print()
    print(f"  {'Rank':<5} {'Fund':<38} {'5yr%':>6}  {'ER%':>5}  {'Net Corpus':>14}  {'Gain':>12}  {'Mult':>6}  Goal")
    print(f"  {'-'*100}")
    for r in result["results"]:
        goal_str = ""
        if result["goal_amount"]:
            goal_str = "YES" if r["hits_goal"] else f"Gap INR {r['goal_gap']:,.0f}"
        print(f"  #{r['rank']:<4} {r['fund_name'][:37]:<38} {r['returns_5yr']:>5.1f}%  "
              f"{r['expense_ratio']:>4.2f}%  {r['net_corpus']:>14,.0f}  "
              f"{r['wealth_gain']:>12,.0f}  {r['wealth_multiplier']:>5.2f}x  {goal_str}")

    print()
    print("  Winner Notes:")
    for note in result["winner_notes"]:
        print(f"    {note}")

    print()
    print("  Detailed Breakdown:")
    for r in result["results"]:
        print(f"  [{r['rank']}] {r['fund_name']}")
        print(f"      Category    : {r['category']}  |  Risk: {r['risk']}  |  ER: {r['expense_ratio']}%")
        print(f"      Returns     : 1yr {r['returns_1yr']}%  3yr {r['returns_3yr']}%  5yr {r['returns_5yr']}%")
        print(f"      Invested    : INR {r['total_invested']:,.0f}")
        print(f"      Gross corpus: INR {r['gross_corpus']:,.0f}")
        print(f"      Expense drag: INR {r['expense_drag_inr']:,.0f}")
        print(f"      Net corpus  : INR {r['net_corpus']:,.0f}")
        print(f"      Multiplier  : {r['wealth_multiplier']}x")
        if result["goal_amount"] and r["sip_needed_for_goal"]:
            print(f"      SIP for goal: INR {r['sip_needed_for_goal']:,.0f}/mo")
        print(f"      Best for    : {r['best_for']}")
        print()


def cmd_fund_list(args):
    """Browse the fund database."""
    from financial_engine.fund_database import FUNDS, CATEGORY_MAP

    category = getattr(args, "category", None)
    fund_type = getattr(args, "fund_type", None)

    funds = FUNDS
    if category:
        keys = CATEGORY_MAP.get(category, [category])
        funds = [f for f in funds if f["category"] in keys]
    if fund_type:
        funds = [f for f in funds if f["fund_type"] == fund_type]

    S = "=" * 62
    print(S); print(f"  FUND DATABASE  ({len(funds)} funds)"); print(S)
    print(f"  {'Fund Name':<42} {'Cat':<18} {'1yr%':>6}  {'3yr%':>6}  {'5yr%':>6}  {'ER%':>5}  Min SIP")
    print(f"  {'-'*105}")
    for f in funds:
        print(f"  {f['name'][:41]:<42} {f['category']:<18} "
              f"{f['returns_1yr']:>5.1f}%  {f['returns_3yr']:>5.1f}%  {f['returns_5yr']:>5.1f}%  "
              f"{f['expense_ratio']:>4.2f}%  INR {f['min_sip']}")
    print()


# ── Argument parser ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AI Financial Decision Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py train                        Train all models
  python main.py evaluate                     Evaluate and generate reports
  python main.py predict                      Interactive predictions
  python main.py run                          Full pipeline (train + evaluate)
  python main.py rules                        Pure rule engine (no ML needed)
  python main.py api                          Start FastAPI server
  python main.py api --port 5000              Custom port

  python main.py stock   RELIANCE.NS          Real-time price + fundamentals
  python main.py signals RELIANCE.NS          Buy/Sell signals
  python main.py score   RELIANCE.NS          Composite stock score
  python main.py rank    RELIANCE.NS TCS.NS INFY.NS
  python main.py sentiment RELIANCE.NS        News sentiment
  python main.py rebalance                    Portfolio rebalancing (interactive)
  python main.py monitor RELIANCE.NS TCS.NS   Start 24/7 watchdog
  python main.py alerts list                  List active alerts
  python main.py alerts add                   Create alert (interactive)
  python main.py alerts delete <ID>           Delete alert
        """,
    )
    parser.add_argument("--dataset",   default="financial_dataset.csv")
    parser.add_argument("--model-dir", default="models")
    parser.add_argument("--output-dir",default="output")

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # Existing
    sub.add_parser("train",    help="Generate dataset and train all models")
    sub.add_parser("evaluate", help="Evaluate saved models")
    sub.add_parser("predict",  help="Interactive prediction mode")
    sub.add_parser("run",      help="Full pipeline: train + evaluate")
    sub.add_parser("rules",    help="Pure if-else engine (zero ML dependencies)")

    ap = sub.add_parser("api", help="Start FastAPI server")
    ap.add_argument("--host",   default="0.0.0.0")
    ap.add_argument("--port",   type=int, default=8000)
    ap.add_argument("--reload", action="store_true")

    # New real-time commands
    sp_stock = sub.add_parser("stock",     help="Price + fundamentals for a ticker")
    sp_stock.add_argument("ticker")

    sp_sig = sub.add_parser("signals",  help="Buy/Sell signals for a ticker")
    sp_sig.add_argument("ticker")
    sp_sig.add_argument("--period", default="6mo", help="History period (default: 6mo)")

    sp_score = sub.add_parser("score",    help="Composite stock score (0-100)")
    sp_score.add_argument("ticker")

    sp_rank = sub.add_parser("rank",     help="Rank multiple stocks by score")
    sp_rank.add_argument("tickers", nargs="+")

    sp_sent = sub.add_parser("sentiment",help="News sentiment for a ticker")
    sp_sent.add_argument("ticker")

    sub.add_parser("rebalance", help="Interactive portfolio rebalancing plan")

    sp_mon = sub.add_parser("monitor",  help="24/7 portfolio watchdog")
    sp_mon.add_argument("tickers", nargs="+")
    sp_mon.add_argument("--price-interval",     type=int, default=300,  dest="price_interval")
    sp_mon.add_argument("--tech-interval",      type=int, default=900,  dest="tech_interval")
    sp_mon.add_argument("--portfolio-interval", type=int, default=3600, dest="portfolio_interval")
    sp_mon.add_argument("--news-interval",      type=int, default=1800, dest="news_interval")

    sp_alr = sub.add_parser("alerts",   help="Manage price/risk alerts")
    alr_sub = sp_alr.add_subparsers(dest="alerts_cmd")
    al_list = alr_sub.add_parser("list")
    al_list.add_argument("--all", action="store_true", help="Include inactive alerts")
    alr_sub.add_parser("add")
    al_del = alr_sub.add_parser("delete")
    al_del.add_argument("alert_id")

    # ── SIP & Fund commands ────────────────────────────────────────────────────
    sp_proj = sub.add_parser("sip-project", help="Project SIP corpus over time")
    sp_proj.add_argument("--sip",      type=float, required=True, help="Monthly SIP in INR")
    sp_proj.add_argument("--years",    type=int,   required=True, help="Horizon in years")
    sp_proj.add_argument("--cagr",     type=float, default=12.0,  help="Annual return % (default 12)")
    sp_proj.add_argument("--step-up",  type=float, default=0.0,   dest="step_up",
                         help="Annual SIP increase % (e.g. 10 = 10%/yr step-up)")
    sp_proj.add_argument("--existing", type=float, default=0.0,   help="Existing corpus in INR")

    sp_gol = sub.add_parser("sip-goal", help="SIP needed / duration to reach a goal")
    sp_gol.add_argument("--target",   type=float, required=True, help="Goal amount in INR")
    sp_gol.add_argument("--years",    type=int,   default=None,  help="Horizon (for SIP-needed calc)")
    sp_gol.add_argument("--sip",      type=float, default=None,  help="Monthly SIP (for duration calc)")
    sp_gol.add_argument("--cagr",     type=float, default=12.0,  help="Annual return %")
    sp_gol.add_argument("--existing", type=float, default=0.0,   help="Existing corpus in INR")

    sp_split = sub.add_parser("sip-split", help="Split SIP across specific named funds")
    sp_split.add_argument("--sip",      type=float, required=True)
    sp_split.add_argument("--risk",     default="medium", choices=["low", "medium", "high"])
    sp_split.add_argument("--goal",     default="wealth",
                          choices=["wealth","education","retirement","house","wedding",
                                   "emergency_fund","tax_saving","vacation"])
    sp_split.add_argument("--years",    type=int,   default=10)
    sp_split.add_argument("--low-cost", action="store_true", dest="low_cost",
                          help="Prefer passive/index funds (lower expense ratio)")

    sp_plan = sub.add_parser("sip-plan",  help="Full SIP plan: funds + projection + goal analysis")
    sp_plan.add_argument("--sip",      type=float, required=True)
    sp_plan.add_argument("--goal",     default="wealth",
                         choices=["wealth","education","retirement","house","wedding",
                                  "emergency_fund","tax_saving","vacation"])
    sp_plan.add_argument("--target",   type=float, default=None,  help="Goal amount in INR")
    sp_plan.add_argument("--years",    type=int,   default=10)
    sp_plan.add_argument("--risk",     default="medium", choices=["low","medium","high"])
    sp_plan.add_argument("--step-up",  type=float, default=10.0,  dest="step_up")
    sp_plan.add_argument("--existing", type=float, default=0.0)
    sp_plan.add_argument("--low-cost", action="store_true", dest="low_cost")

    sp_cmp = sub.add_parser("fund-compare", help="Compare Fund A vs Fund B for a goal")
    sp_cmp.add_argument("funds",       nargs="+",  help="Fund names or ids to compare")
    sp_cmp.add_argument("--sip",       type=float, required=True)
    sp_cmp.add_argument("--years",     type=int,   required=True)
    sp_cmp.add_argument("--target",    type=float, default=None,  help="Goal amount in INR")
    sp_cmp.add_argument("--existing",  type=float, default=0.0)
    sp_cmp.add_argument("--step-up",   type=float, default=0.0,   dest="step_up")

    sp_fl = sub.add_parser("fund-list", help="Browse all funds in the database")
    sp_fl.add_argument("--category",   default=None,
                       help="Filter by category (large_cap, mid_cap, debt, liquid, gold, ...)")
    sp_fl.add_argument("--fund-type",  default=None, dest="fund_type",
                       choices=["equity", "debt", "hybrid", "commodity"])

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "train":     cmd_train,
        "evaluate":  cmd_evaluate,
        "predict":   cmd_predict,
        "run":       cmd_run,
        "rules":     cmd_rules,
        "api":       cmd_api,
        "stock":     cmd_stock,
        "signals":   cmd_signals,
        "score":     cmd_score,
        "rank":      cmd_rank,
        "sentiment": cmd_sentiment,
        "rebalance":    cmd_rebalance,
        "monitor":      cmd_monitor,
        "alerts":       cmd_alerts,
        "sip-project":  cmd_sip_project,
        "sip-goal":     cmd_sip_goal,
        "sip-split":    cmd_sip_split,
        "sip-plan":     cmd_sip_plan,
        "fund-compare": cmd_fund_compare,
        "fund-list":    cmd_fund_list,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()

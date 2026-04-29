"""
stock_scorer.py - Stock scoring and ranking system

Composite score 0-100 built from four sub-scores:
  Fundamental  30% : PE, EPS growth, debt, ROE, margins
  Technical    40% : RSI/MACD/MA momentum (from signal_engine)
  Valuation    20% : analyst target, 52-week position, PEG
  Sentiment    10% : news mood (from sentiment_analyzer)

Grades: A (80+) B (65+) C (50+) D (35+) F (<35)
"""

from typing import List
from .stock_data_fetcher import get_fundamentals, get_stock_price
from .signal_engine import generate_signals
from .sentiment_analyzer import get_stock_sentiment


# ── Sub-score helpers ──────────────────────────────────────────────────────────

def _fundamental_score(fundamentals: dict) -> tuple:
    score = 50
    reasons = []

    pe = fundamentals.get("pe_ratio")
    if pe:
        if   0  < pe < 15: score += 15; reasons.append(f"Low PE ({pe:.1f})")
        elif pe <= 25:      score +=  8; reasons.append(f"Fair PE ({pe:.1f})")
        elif pe <= 40:      score -=  5; reasons.append(f"High PE ({pe:.1f})")
        else:               score -= 15; reasons.append(f"Very high PE ({pe:.1f})")

    eg = fundamentals.get("earnings_growth")
    if eg is not None:
        if   eg > 0.30: score += 12; reasons.append(f"Strong earnings growth ({eg*100:.1f}%)")
        elif eg > 0.10: score +=  6; reasons.append(f"Moderate earnings growth ({eg*100:.1f}%)")
        elif eg < 0:    score -= 10; reasons.append(f"Declining earnings ({eg*100:.1f}%)")

    de = fundamentals.get("debt_to_equity")
    if de is not None:
        if   de < 0.3:  score += 10; reasons.append(f"Low debt (D/E={de:.2f})")
        elif de < 1.0:  score +=  3; reasons.append(f"Moderate debt (D/E={de:.2f})")
        elif de > 3.0:  score -= 20; reasons.append(f"Very high debt (D/E={de:.2f})")
        elif de > 2.0:  score -= 12; reasons.append(f"High debt (D/E={de:.2f})")

    roe = fundamentals.get("roe")
    if roe:
        if   roe > 0.20: score += 10; reasons.append(f"Excellent ROE ({roe*100:.1f}%)")
        elif roe > 0.12: score +=  5; reasons.append(f"Good ROE ({roe*100:.1f}%)")
        elif roe < 0:    score -= 10; reasons.append(f"Negative ROE ({roe*100:.1f}%)")

    pm = fundamentals.get("profit_margin")
    if pm:
        if   pm > 0.20: score +=  8; reasons.append(f"High margin ({pm*100:.1f}%)")
        elif pm > 0.10: score +=  4; reasons.append(f"Good margin ({pm*100:.1f}%)")
        elif pm < 0:    score -=  8; reasons.append(f"Negative margin ({pm*100:.1f}%)")

    dy = fundamentals.get("dividend_yield")
    if dy and dy > 0:
        if   dy > 0.05: score += 5; reasons.append(f"High dividend ({dy*100:.1f}%)")
        elif dy > 0.02: score += 2; reasons.append(f"Dividend yield ({dy*100:.1f}%)")

    return max(0, min(100, score)), reasons


def _valuation_score(fundamentals: dict, price_data: dict) -> tuple:
    score = 50
    reasons = []

    price = price_data.get("current_price", 0)
    target = fundamentals.get("target_price")
    if price and target and target > 0:
        upside = (target - price) / price
        if   upside > 0.30: score += 25; reasons.append(f"High analyst upside ({upside*100:.1f}%)")
        elif upside > 0.10: score += 12; reasons.append(f"Analyst upside ({upside*100:.1f}%)")
        elif upside < -0.10: score -= 15; reasons.append(f"Above analyst target ({upside*100:.1f}%)")

    h52 = fundamentals.get("52w_high", 0)
    l52 = fundamentals.get("52w_low", 0)
    if price and h52 and l52 and h52 > l52:
        pfl = (price - l52) / (h52 - l52)
        if   pfl < 0.30: score += 15; reasons.append(f"Near 52w low ({pfl*100:.0f}% of range)")
        elif pfl < 0.50: score +=  5; reasons.append("Below mid 52w range")
        elif pfl > 0.90: score -= 10; reasons.append(f"Near 52w high ({pfl*100:.0f}%)")

    peg = fundamentals.get("peg_ratio")
    if peg:
        if   0 < peg < 1.0:  score += 12; reasons.append(f"Excellent PEG ({peg:.2f})")
        elif peg <= 1.5:      score +=  5; reasons.append(f"Fair PEG ({peg:.2f})")
        elif peg > 2.0:       score -=  8; reasons.append(f"High PEG ({peg:.2f})")

    rec = fundamentals.get("analyst_recommendation")
    if rec:
        # 1=Strong Buy, 5=Sell
        if   rec <= 1.5: score += 15; reasons.append(f"Strong consensus BUY ({rec:.1f})")
        elif rec <= 2.5: score +=  8; reasons.append(f"Consensus BUY ({rec:.1f})")
        elif rec >= 4.0: score -= 15; reasons.append(f"Consensus SELL ({rec:.1f})")
        elif rec >= 3.5: score -=  5; reasons.append(f"Consensus UNDERPERFORM ({rec:.1f})")

    return max(0, min(100, score)), reasons


# ── Public API ─────────────────────────────────────────────────────────────────

def score_stock(ticker: str, owned_tickers: list = None) -> dict:
    """
    Composite 0-100 score for a stock.

    Parameters
    ----------
    ticker        : NSE/BSE ticker symbol (e.g. "RELIANCE.NS")
    owned_tickers : List of tickers the user already holds in their portfolio.
                    When provided, BUY/STRONG BUY recommendations are adjusted:
                      - "ADD_MORE"   if technically still a buy signal
                      - "HOLD"       if technically neutral
                    SELL signals are always preserved regardless of ownership.

    breakdown keys: fundamental, technical, valuation, sentiment
    """
    fundamentals = get_fundamentals(ticker)
    price_data   = get_stock_price(ticker)
    signals      = generate_signals(ticker)
    sentiment    = get_stock_sentiment(ticker)

    if "error" in fundamentals and "error" in price_data:
        return {"ticker": ticker, "error": "Could not fetch data", "score": 0}

    fund_score,  fund_reasons  = _fundamental_score(fundamentals)
    val_score,   val_reasons   = _valuation_score(fundamentals, price_data)

    # Technical: signal score -1..+1  →  0..100
    tech_raw   = signals.get("score", 0.0)
    tech_score = int((tech_raw + 1) / 2 * 100)
    tech_reasons = signals.get("reasons", [])

    # Sentiment: score -1..+1  →  0..100
    sent_raw   = sentiment.get("score", 0.0)
    sent_score = int((sent_raw + 1) / 2 * 100)

    composite = round(
        fund_score * 0.30 +
        tech_score * 0.40 +
        val_score  * 0.20 +
        sent_score * 0.10,
        1,
    )

    if   composite >= 80: grade, recommendation = "A", "STRONG BUY"
    elif composite >= 65: grade, recommendation = "B", "BUY"
    elif composite >= 50: grade, recommendation = "C", "HOLD"
    elif composite >= 35: grade, recommendation = "D", "SELL"
    else:                  grade, recommendation = "F", "STRONG SELL"

    # Ownership-aware recommendation adjustment
    owned_set = set(t.upper() for t in (owned_tickers or []))
    already_owned = ticker.upper() in owned_set
    ownership_note = None

    if already_owned:
        if recommendation == "STRONG BUY":
            recommendation = "ADD_MORE"
            ownership_note = "You already own this. Consider adding more — strong fundamentals support a larger position."
        elif recommendation == "BUY":
            recommendation = "ADD_MORE"
            ownership_note = "You already own this. Signals are positive — you can add to your existing position."
        elif recommendation in ("SELL", "STRONG SELL"):
            ownership_note = "You hold this stock. Signals are weak — consider reducing or exiting your position."
        else:
            ownership_note = "You already own this. Hold and monitor."

    return {
        "ticker": ticker,
        "name": fundamentals.get("name", ticker),
        "score": composite,
        "grade": grade,
        "recommendation": recommendation,
        "already_owned": already_owned,
        "ownership_note": ownership_note,
        "current_price": price_data.get("current_price"),
        "change_pct": price_data.get("change_pct"),
        "breakdown": {
            "fundamental": {"score": fund_score, "weight": "30%", "reasons": fund_reasons},
            "technical":   {"score": tech_score, "weight": "40%",
                            "signal": signals.get("signal"), "strength": signals.get("strength"),
                            "reasons": tech_reasons},
            "valuation":   {"score": val_score,  "weight": "20%", "reasons": val_reasons},
            "sentiment":   {"score": sent_score, "weight": "10%",
                            "mood": sentiment.get("mood"), "summary": sentiment.get("summary")},
        },
        "key_metrics": {
            "pe_ratio":       fundamentals.get("pe_ratio"),
            "eps_ttm":        fundamentals.get("eps_ttm"),
            "debt_to_equity": fundamentals.get("debt_to_equity"),
            "roe":            fundamentals.get("roe"),
            "dividend_yield": fundamentals.get("dividend_yield"),
            "target_price":   fundamentals.get("target_price"),
            "beta":           fundamentals.get("beta"),
            "market_cap":     fundamentals.get("market_cap"),
        },
    }


def rank_stocks(tickers: List[str], owned_tickers: list = None) -> List[dict]:
    """
    Score and rank a list of tickers (highest score first).

    Parameters
    ----------
    tickers       : Tickers to score and rank.
    owned_tickers : Tickers the user already holds. Passed into score_stock()
                    so BUY signals become ADD_MORE for owned stocks.
    """
    scores = [score_stock(t, owned_tickers=owned_tickers) for t in tickers]
    scores.sort(key=lambda x: x.get("score", 0), reverse=True)
    for i, s in enumerate(scores):
        s["rank"] = i + 1
    return scores

"""
sentiment_analyzer.py - News and market sentiment analysis

Keyword-based scoring — no ML dependencies required.

Score range: -1.0 (very bearish) to +1.0 (very bullish)
Mood labels: BEARISH | SLIGHTLY_BEARISH | NEUTRAL | SLIGHTLY_BULLISH | BULLISH
"""

from typing import List
from .stock_data_fetcher import get_stock_news

# ── Keyword dictionaries ───────────────────────────────────────────────────────

BULLISH_KEYWORDS = {
    "surge": 2.0, "soars": 2.0, "rally": 2.0, "record high": 2.0,
    "beats": 2.0, "upgrades": 2.0, "upgrade": 2.0, "outperform": 2.0,
    "strong results": 2.0, "above expectations": 2.0, "bullish": 2.0,
    "acquisition": 1.5, "dividend": 1.5, "buyback": 1.5, "exceeds": 1.5,
    "upside": 1.5, "buy": 1.0, "rise": 1.0, "gain": 1.0, "growth": 1.0,
    "profit": 1.0, "increase": 1.0, "expand": 1.0, "higher": 1.0,
    "recovery": 1.0, "opportunity": 1.0, "positive": 1.0, "strong": 1.0,
    "momentum": 1.0, "invest": 1.0,
}

BEARISH_KEYWORDS = {
    "fraud": 3.0, "bankrupt": 3.0, "scandal": 2.5, "default": 2.5,
    "crash": 2.0, "plunge": 2.0, "collapse": 2.0, "downgrade": 2.0,
    "underperform": 2.0, "probe": 1.5, "investigation": 2.0,
    "below expectations": 2.0, "bearish": 2.0, "warning": 1.5,
    "layoff": 1.5, "loss": 1.5, "miss": 1.5, "weak": 1.5,
    "sell": 1.0, "fall": 1.0, "drop": 1.0, "decline": 1.0,
    "lower": 1.0, "negative": 1.0, "concern": 1.0, "cut": 1.0,
    "reduce": 1.0, "uncertainty": 1.0, "volatile": 0.5, "risk": 0.5,
}


def _score_text(text: str) -> float:
    """Return sentiment score -1.0..+1.0 for a text string."""
    t = text.lower()
    bull = sum(w for kw, w in BULLISH_KEYWORDS.items() if kw in t)
    bear = sum(w for kw, w in BEARISH_KEYWORDS.items() if kw in t)
    total = bull + bear
    if total == 0:
        return 0.0
    return round(max(-1.0, min(1.0, (bull - bear) / total)), 3)


def _mood_label(score: float) -> str:
    if   score >  0.30: return "BULLISH"
    if   score >  0.05: return "SLIGHTLY_BULLISH"
    if   score < -0.30: return "BEARISH"
    if   score < -0.05: return "SLIGHTLY_BEARISH"
    return "NEUTRAL"


def analyze_article_sentiment(title: str, description: str = "") -> dict:
    """Sentiment for a single article (title + description)."""
    score = _score_text(f"{title} {description}")
    return {"title": title, "sentiment_score": score, "mood": _mood_label(score)}


def get_stock_sentiment(ticker: str, news_count: int = 10) -> dict:
    """
    Aggregate news sentiment for one ticker.

    Returns: ticker, score, mood, num_articles, article_sentiments (top 5), summary
    """
    news = get_stock_news(ticker, count=news_count)

    if not news:
        return {
            "ticker": ticker, "score": 0.0, "mood": "NEUTRAL",
            "num_articles": 0, "article_sentiments": [],
            "summary": "No recent news available",
        }

    article_sentiments = []
    scores = []
    for item in news:
        title = item.get("title", "")
        if not title:
            continue
        s = _score_text(title)
        scores.append(s)
        article_sentiments.append({
            "title": title[:100],
            "score": s,
            "mood": _mood_label(s),
            "published": item.get("published", ""),
            "publisher": item.get("publisher", ""),
        })

    if not scores:
        return {
            "ticker": ticker, "score": 0.0, "mood": "NEUTRAL",
            "num_articles": 0, "article_sentiments": [],
            "summary": "Could not parse news",
        }

    avg = round(sum(scores) / len(scores), 3)
    bull_c = sum(1 for s in scores if s > 0.05)
    bear_c = sum(1 for s in scores if s < -0.05)
    mood   = _mood_label(avg)

    summary = (
        f"{ticker}: {mood} from {len(scores)} articles "
        f"({bull_c} bullish, {bear_c} bearish, "
        f"{len(scores)-bull_c-bear_c} neutral)"
    )

    return {
        "ticker": ticker,
        "score": avg,
        "mood": mood,
        "num_articles": len(scores),
        "bullish_count": bull_c,
        "bearish_count": bear_c,
        "neutral_count": len(scores) - bull_c - bear_c,
        "article_sentiments": article_sentiments[:5],
        "summary": summary,
    }


def get_market_sentiment(tickers: List[str]) -> dict:
    """Aggregate sentiment across a basket of tickers."""
    individual = {}
    scores = []

    for ticker in tickers:
        s = get_stock_sentiment(ticker, news_count=5)
        individual[ticker] = s
        if s.get("num_articles", 0) > 0:
            scores.append(s["score"])

    if not scores:
        return {
            "market_score": 0.0, "market_mood": "NEUTRAL",
            "stocks_analyzed": len(tickers), "individual": individual,
            "summary": "Insufficient news data",
        }

    mkt_score  = round(sum(scores) / len(scores), 3)
    bull_stocks = sum(1 for s in scores if s > 0.05)
    bear_stocks = sum(1 for s in scores if s < -0.05)
    mood        = _mood_label(mkt_score)

    return {
        "market_score": mkt_score,
        "market_mood": mood,
        "stocks_analyzed": len(scores),
        "bullish_stocks": bull_stocks,
        "bearish_stocks": bear_stocks,
        "individual": individual,
        "summary": (
            f"Market {mood}: {bull_stocks}/{len(scores)} stocks bullish, "
            f"{bear_stocks}/{len(scores)} bearish"
        ),
    }

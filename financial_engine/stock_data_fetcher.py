"""
stock_data_fetcher.py - Real-time stock data via yfinance

Provides:
- Current price, change, volume
- Fundamentals: PE, EPS, debt/equity, market cap
- Historical OHLCV data
- In-memory caching to avoid rate limits
"""

import time
from datetime import datetime

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

import pandas as pd
import numpy as np

# In-memory cache: key -> (timestamp, value)
_cache: dict = {}
_cache_ttl = 300  # 5 minutes


def _is_cached(key: str) -> bool:
    if key not in _cache:
        return False
    ts, _ = _cache[key]
    return (time.time() - ts) < _cache_ttl


def _get_cached(key: str):
    return _cache[key][1]


def _set_cache(key: str, value):
    _cache[key] = (time.time(), value)


def get_stock_price(ticker: str) -> dict:
    """Get current price, change %, volume for a ticker."""
    if not YFINANCE_AVAILABLE:
        return {"error": "yfinance not installed", "ticker": ticker}

    cache_key = f"price_{ticker}"
    if _is_cached(cache_key):
        return _get_cached(cache_key)

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        current_price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose", 0)
        )
        prev_close = (
            info.get("previousClose")
            or info.get("regularMarketPreviousClose")
            or current_price
        )
        change = current_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        result = {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName", ticker),
            "current_price": round(float(current_price), 2),
            "previous_close": round(float(prev_close), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "volume": info.get("regularMarketVolume") or info.get("volume", 0),
            "avg_volume": info.get("averageVolume", 0),
            "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh", 0),
            "day_low": info.get("dayLow") or info.get("regularMarketDayLow", 0),
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "currency": info.get("currency", "INR"),
            "exchange": info.get("exchange", ""),
            "timestamp": datetime.now().isoformat(),
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def get_fundamentals(ticker: str) -> dict:
    """Get PE, EPS, debt/equity, ROE, market cap, analyst targets."""
    if not YFINANCE_AVAILABLE:
        return {"error": "yfinance not installed", "ticker": ticker}

    cache_key = f"fundamentals_{ticker}"
    if _is_cached(cache_key):
        return _get_cached(cache_key)

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        result = {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName", ticker),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            # Valuation
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "ev_to_ebitda": info.get("enterpriseToEbitda"),
            # Earnings
            "eps_ttm": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "earnings_growth": info.get("earningsGrowth"),
            "revenue_growth": info.get("revenueGrowth"),
            # Profitability
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            # Debt
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "total_debt": info.get("totalDebt"),
            # Dividends
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "payout_ratio": info.get("payoutRatio"),
            # Analyst
            "target_price": info.get("targetMeanPrice"),
            "analyst_recommendation": info.get("recommendationMean"),
            "num_analyst_opinions": info.get("numberOfAnalystOpinions", 0),
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "beta": info.get("beta"),
            "timestamp": datetime.now().isoformat(),
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def get_historical_data(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """
    Get OHLCV historical data.

    period:   1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y
    interval: 1m, 5m, 15m, 1h, 1d, 1wk, 1mo
    """
    if not YFINANCE_AVAILABLE:
        return pd.DataFrame()

    cache_key = f"hist_{ticker}_{period}_{interval}"
    if _is_cached(cache_key):
        return _get_cached(cache_key)

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index = pd.to_datetime(df.index)
        _set_cache(cache_key, df)
        return df
    except Exception as e:
        print(f"Error fetching history for {ticker}: {e}")
        return pd.DataFrame()


def get_multiple_stocks(tickers: list) -> dict:
    """Batch-fetch price + fundamentals for multiple tickers."""
    results = {}
    for ticker in tickers:
        results[ticker] = {
            "price": get_stock_price(ticker),
            "fundamentals": get_fundamentals(ticker),
        }
        time.sleep(0.15)  # rate-limit courtesy
    return results


def get_stock_news(ticker: str, count: int = 10) -> list:
    """Get recent news articles for a ticker via yfinance."""
    if not YFINANCE_AVAILABLE:
        return []

    cache_key = f"news_{ticker}"
    if _is_cached(cache_key):
        return _get_cached(cache_key)

    try:
        stock = yf.Ticker(ticker)
        news = stock.news or []
        result = []
        for item in news[:count]:
            pub_ts = item.get("providerPublishTime", 0)
            result.append({
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "link": item.get("link", ""),
                "published": (
                    datetime.fromtimestamp(pub_ts).isoformat() if pub_ts else ""
                ),
                "type": item.get("type", ""),
            })
        _set_cache(cache_key, result)
        return result
    except Exception:
        return []


def clear_cache():
    """Clear the in-memory data cache."""
    global _cache
    _cache = {}

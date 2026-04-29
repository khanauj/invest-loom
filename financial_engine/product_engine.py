"""
product_engine.py - Real-Time Investment Product Data Engine

Fetches live NAV, 1yr returns, 52-week range from yfinance
for Indian mutual funds & ETFs mapped to each action type.

No LLM. Pure data fetching.
"""

import yfinance as yf


# ──────────────────────────────────────────────
#  Product Universe — Indian Mutual Funds & ETFs
# ──────────────────────────────────────────────

PRODUCT_CATALOG = {
    "equity_index": [
        {"symbol": "0P0000XVAP.BO", "name": "HDFC Index Fund Nifty 50", "category": "Large Cap Index", "type": "equity"},
        {"symbol": "0P0001BAQ7.BO", "name": "UTI Nifty 50 Index Fund", "category": "Large Cap Index", "type": "equity"},
        {"symbol": "0P00017YJG.BO", "name": "Motilal Oswal Nasdaq 100 FoF", "category": "International Equity", "type": "equity"},
        {"symbol": "0P0001I9T6.BO", "name": "Parag Parikh Flexi Cap Fund", "category": "Flexi Cap", "type": "equity"},
    ],
    "equity_active": [
        {"symbol": "0P0000XVJ7.BO", "name": "Mirae Asset Large Cap Fund", "category": "Large Cap", "type": "equity"},
        {"symbol": "0P0000XVLF.BO", "name": "Axis Bluechip Fund", "category": "Large Cap", "type": "equity"},
        {"symbol": "0P0000XVAA.BO", "name": "SBI Small Cap Fund", "category": "Small Cap", "type": "equity"},
        {"symbol": "0P0000XVHK.BO", "name": "Kotak Emerging Equity Fund", "category": "Mid Cap", "type": "equity"},
    ],
    "debt": [
        {"symbol": "0P0000XVEZ.BO", "name": "HDFC Short Term Debt Fund", "category": "Short Duration", "type": "debt"},
        {"symbol": "0P0000XVC3.BO", "name": "ICICI Pru Corporate Bond Fund", "category": "Corporate Bond", "type": "debt"},
        {"symbol": "0P0001H4GJ.BO", "name": "SBI Magnum Gilt Fund", "category": "Gilt", "type": "debt"},
        {"symbol": "0P0000XVF1.BO", "name": "Axis Banking & PSU Debt Fund", "category": "Banking & PSU", "type": "debt"},
    ],
    "hybrid": [
        {"symbol": "0P0000XVBM.BO", "name": "ICICI Pru Balanced Advantage Fund", "category": "Balanced Advantage", "type": "hybrid"},
        {"symbol": "0P0000XVAP.BO", "name": "HDFC Balanced Advantage Fund", "category": "Balanced Advantage", "type": "hybrid"},
    ],
}

# Map actions to relevant product categories
ACTION_TO_PRODUCTS = {
    "INCREASE_SIP":         ["equity_index", "equity_active"],
    "START_SIP":            ["equity_index", "hybrid"],
    "CONTINUE_SIP":         ["equity_index"],
    "BUY":                  ["equity_active", "equity_index"],
    "SWITCH_TO_EQUITY":     ["equity_index", "equity_active"],
    "SWITCH_TO_DEBT":       ["debt"],
    "REBALANCE":            ["debt", "hybrid"],
    "DIVERSIFY_PORTFOLIO":  ["equity_index", "debt", "hybrid"],
    "SELL":                 ["debt"],
    "REDUCE_SIP":           ["debt", "hybrid"],
    "EMERGENCY_FUND_BUILD": ["debt"],
    "STOP_SIP":             [],
    "HOLD":                 [],
}


def _fetch_fund_data(symbol, name, category, type):
    """Fetch real-time fund data from yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")

        if hist.empty:
            return None

        current_nav = round(float(hist["Close"].iloc[-1]), 2)
        nav_1y_ago = round(float(hist["Close"].iloc[0]), 2)
        return_1y = round(((current_nav - nav_1y_ago) / nav_1y_ago) * 100, 2)

        high_52w = round(float(hist["Close"].max()), 2)
        low_52w = round(float(hist["Close"].min()), 2)

        return {
            "name": name,
            "symbol": symbol,
            "category": category,
            "type": type,
            "current_nav": current_nav,
            "return_1y": return_1y,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "data_available": True,
        }
    except Exception:
        return {
            "name": name,
            "symbol": symbol,
            "category": category,
            "type": type,
            "data_available": False,
        }


def fetch_products_for_action(action):
    """Fetch real-time data for all products relevant to the given action."""
    categories = ACTION_TO_PRODUCTS.get(action, [])
    if not categories:
        return []

    products = []
    seen = set()
    for cat in categories:
        for prod in PRODUCT_CATALOG.get(cat, []):
            if prod["symbol"] not in seen:
                seen.add(prod["symbol"])
                data = _fetch_fund_data(**prod)
                if data:
                    products.append(data)

    products.sort(key=lambda x: x.get("return_1y", -999) if x.get("data_available") else -9999, reverse=True)
    return products

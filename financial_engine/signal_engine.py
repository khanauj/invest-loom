"""
signal_engine.py - Buy/Sell/Hold signal generation

Each indicator casts a vote in [-1, +1].
Votes are weighted and aggregated into a composite score.

Score thresholds:
  >= +0.40  -> BUY  STRONG
  >= +0.15  -> BUY  MODERATE
  >= +0.05  -> BUY  WEAK
  <= -0.40  -> SELL STRONG
  <= -0.15  -> SELL MODERATE
  <= -0.05  -> SELL WEAK
  otherwise -> HOLD NEUTRAL
"""

from .stock_data_fetcher import get_historical_data
from .technical_indicators import get_all_indicators

SIGNAL_WEIGHTS = {
    "rsi":         0.20,
    "macd":        0.25,
    "ma_trend":    0.20,
    "bollinger":   0.15,
    "stochastic":  0.10,
    "volume":      0.10,
}


# ── Individual indicator signal functions ─────────────────────────────────────

def _rsi_signal(rsi: float) -> tuple:
    if rsi >= 80:
        return -1.0, f"Extremely overbought (RSI={rsi:.1f})"
    if rsi >= 70:
        return -0.6, f"Overbought (RSI={rsi:.1f})"
    if rsi <= 20:
        return  1.0, f"Extremely oversold (RSI={rsi:.1f})"
    if rsi <= 30:
        return  0.6, f"Oversold (RSI={rsi:.1f})"
    if 40 <= rsi <= 60:
        return  0.0, f"Neutral RSI ({rsi:.1f})"
    if rsi < 40:
        return -0.2, f"Weak RSI ({rsi:.1f})"
    return 0.2, f"Healthy RSI ({rsi:.1f})"


def _macd_signal(macd: float, signal: float, histogram: float) -> tuple:
    if macd > signal and histogram > 0:
        strength = min(abs(histogram) * 10, 1.0)
        return min(0.8, strength), f"MACD bullish (hist={histogram:.4f})"
    if macd < signal and histogram < 0:
        strength = min(abs(histogram) * 10, 1.0)
        return -min(0.8, strength), f"MACD bearish (hist={histogram:.4f})"
    return 0.0, "MACD neutral"


def _ma_trend_signal(price: float, sma_20, sma_50, sma_200) -> tuple:
    signals, reasons = [], []

    if sma_20 is not None:
        ratio = price / sma_20
        if ratio > 1.02:
            signals.append(0.5); reasons.append(f"Price above SMA20 (+{(ratio-1)*100:.1f}%)")
        elif ratio < 0.98:
            signals.append(-0.5); reasons.append(f"Price below SMA20 ({(ratio-1)*100:.1f}%)")
        else:
            signals.append(0.0); reasons.append("Price near SMA20")

    if sma_50 is not None:
        ratio = price / sma_50
        if ratio > 1.02:
            signals.append(0.4); reasons.append("Price above SMA50")
        elif ratio < 0.98:
            signals.append(-0.4); reasons.append("Price below SMA50")
        else:
            signals.append(0.0)

    if sma_200 is not None:
        if price > sma_200:
            signals.append(0.3); reasons.append("Above 200-day MA (bull trend)")
        else:
            signals.append(-0.3); reasons.append("Below 200-day MA (bear trend)")

    if sma_20 is not None and sma_50 is not None:
        if sma_20 > sma_50 * 1.01:
            signals.append(0.3); reasons.append("Golden cross (SMA20 > SMA50)")
        elif sma_20 < sma_50 * 0.99:
            signals.append(-0.3); reasons.append("Death cross (SMA20 < SMA50)")

    avg = sum(signals) / len(signals) if signals else 0.0
    return round(avg, 3), "; ".join(reasons)


def _bollinger_signal(pct_b: float) -> tuple:
    if pct_b is None:
        return 0.0, "Bollinger N/A"
    if pct_b > 1.0:
        return -0.7, f"Above upper BB (overbought, %B={pct_b:.2f})"
    if pct_b > 0.8:
        return -0.3, f"Near upper BB (%B={pct_b:.2f})"
    if pct_b < 0.0:
        return  0.7, f"Below lower BB (oversold, %B={pct_b:.2f})"
    if pct_b < 0.2:
        return  0.3, f"Near lower BB (%B={pct_b:.2f})"
    return 0.0, f"Within BB (%B={pct_b:.2f})"


def _stochastic_signal(k: float, d: float) -> tuple:
    if k >= 80 and d >= 80:
        return -0.6, f"Stoch overbought (K={k:.1f}, D={d:.1f})"
    if k <= 20 and d <= 20:
        return  0.6, f"Stoch oversold (K={k:.1f}, D={d:.1f})"
    if k > d and k < 80:
        return  0.3, f"Stoch bullish cross (K={k:.1f} > D={d:.1f})"
    if k < d and k > 20:
        return -0.3, f"Stoch bearish cross (K={k:.1f} < D={d:.1f})"
    return 0.0, f"Stoch neutral (K={k:.1f})"


def _volume_signal(vol_ratio: float) -> tuple:
    if vol_ratio is None:
        return 0.0, "Volume N/A"
    if vol_ratio >= 2.0:
        return  0.30, f"High volume confirmation ({vol_ratio:.1f}x avg)"
    if vol_ratio >= 1.5:
        return  0.15, f"Above-avg volume ({vol_ratio:.1f}x avg)"
    if vol_ratio < 0.5:
        return -0.10, f"Low volume — weak signal ({vol_ratio:.1f}x avg)"
    return 0.0, f"Normal volume ({vol_ratio:.1f}x avg)"


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_signals(ticker: str, period: str = "6mo") -> dict:
    """
    Generate BUY / SELL / HOLD signal with strength and per-indicator breakdown.

    Returns:
        ticker, signal, strength, score, current_price,
        indicators (dict), reasons (list), period
    """
    hist = get_historical_data(ticker, period=period)
    base = {"ticker": ticker, "signal": "HOLD", "strength": "WEAK",
            "score": 0.0, "indicators": {}, "reasons": []}

    if hist.empty:
        return {**base, "error": "Insufficient historical data"}

    ind = get_all_indicators(hist)
    if not ind:
        return {**base, "error": "Could not calculate indicators"}

    rsi_s,   rsi_r   = _rsi_signal(ind["rsi"] or 50)
    macd_s,  macd_r  = _macd_signal(ind["macd"] or 0, ind["macd_signal"] or 0, ind["macd_histogram"] or 0)
    ma_s,    ma_r    = _ma_trend_signal(ind["current_price"], ind.get("sma_20"), ind.get("sma_50"), ind.get("sma_200"))
    bb_s,    bb_r    = _bollinger_signal(ind.get("bb_pct_b"))
    stoch_s, stoch_r = _stochastic_signal(ind.get("stoch_k") or 50, ind.get("stoch_d") or 50)
    vol_s,   vol_r   = _volume_signal(ind.get("volume_signal"))

    w = SIGNAL_WEIGHTS
    score = round(max(-1.0, min(1.0,
        rsi_s   * w["rsi"]         +
        macd_s  * w["macd"]        +
        ma_s    * w["ma_trend"]    +
        bb_s    * w["bollinger"]   +
        stoch_s * w["stochastic"]  +
        vol_s   * w["volume"]
    )), 3)

    if   score >=  0.40: signal, strength = "BUY",  "STRONG"
    elif score >=  0.15: signal, strength = "BUY",  "MODERATE"
    elif score >=  0.05: signal, strength = "BUY",  "WEAK"
    elif score <= -0.40: signal, strength = "SELL", "STRONG"
    elif score <= -0.15: signal, strength = "SELL", "MODERATE"
    elif score <= -0.05: signal, strength = "SELL", "WEAK"
    else:                signal, strength = "HOLD", "NEUTRAL"

    return {
        "ticker": ticker,
        "signal": signal,
        "strength": strength,
        "score": score,
        "current_price": ind["current_price"],
        "indicators": {
            "rsi":             {"value": ind["rsi"],            "score": round(rsi_s,   3), "reason": rsi_r},
            "macd":            {"value": ind["macd"],           "signal_line": ind["macd_signal"],
                                "histogram": ind["macd_histogram"], "score": round(macd_s, 3), "reason": macd_r},
            "moving_averages": {"sma_20": ind.get("sma_20"),    "sma_50": ind.get("sma_50"),
                                "sma_200": ind.get("sma_200"),  "score": round(ma_s,    3), "reason": ma_r},
            "bollinger_bands": {"upper": ind["bb_upper"],       "middle": ind["bb_middle"],
                                "lower": ind["bb_lower"],       "pct_b": ind["bb_pct_b"],
                                "score": round(bb_s,   3), "reason": bb_r},
            "stochastic":      {"k": ind["stoch_k"],            "d": ind["stoch_d"],
                                "score": round(stoch_s, 3), "reason": stoch_r},
            "volume":          {"ratio": ind["volume_signal"],  "score": round(vol_s,   3), "reason": vol_r},
            "adx":             ind.get("adx"),
        },
        "reasons": [r for r in [rsi_r, macd_r, ma_r, bb_r, stoch_r, vol_r] if r],
        "period": period,
    }

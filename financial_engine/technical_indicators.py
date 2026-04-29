"""
technical_indicators.py - Technical indicator calculations (pure numpy/pandas)

Implements:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Simple & Exponential Moving Averages
- Bollinger Bands
- Stochastic Oscillator
- ATR (Average True Range)
- ADX (Average Directional Index)
- Volume ratio
"""

import numpy as np
import pandas as pd


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI (0-100). >70 overbought, <30 oversold."""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def calculate_macd(
    prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """MACD line, signal line, histogram."""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame(
        {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": macd_line - signal_line,
        }
    )


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return prices.rolling(window=period).mean()


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return prices.ewm(span=period, adjust=False).mean()


def calculate_bollinger_bands(
    prices: pd.Series, period: int = 20, std_dev: float = 2.0
) -> pd.DataFrame:
    """Bollinger Bands: middle (SMA20), upper, lower, %B, bandwidth."""
    sma = calculate_sma(prices, period)
    std = prices.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    pct_b = (prices - lower) / (upper - lower)
    return pd.DataFrame(
        {
            "middle": sma,
            "upper": upper,
            "lower": lower,
            "bandwidth": (upper - lower) / sma,
            "pct_b": pct_b,
        }
    )


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> pd.DataFrame:
    """Stochastic %K and %D."""
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(window=d_period).mean()
    return pd.DataFrame({"k": k.fillna(50), "d": d.fillna(50)})


def calculate_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """Average True Range — volatility measure."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()


def calculate_adx(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.DataFrame:
    """ADX, +DI, -DI — trend strength (ADX>25 = strong trend)."""
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    plus_dm = (high - prev_high).clip(lower=0)
    minus_dm = (prev_low - low).clip(lower=0)
    plus_dm = plus_dm.where(plus_dm > minus_dm, 0)
    minus_dm = minus_dm.where(minus_dm > plus_dm, 0)

    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(com=period - 1, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(com=period - 1, min_periods=period).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(com=period - 1, min_periods=period).mean() / atr.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(com=period - 1, min_periods=period).mean()

    return pd.DataFrame(
        {
            "adx": adx.fillna(0),
            "plus_di": plus_di.fillna(0),
            "minus_di": minus_di.fillna(0),
        }
    )


def calculate_volume_signal(volume: pd.Series, period: int = 20) -> pd.Series:
    """Volume relative to its moving average (>1 = above average)."""
    avg = calculate_sma(volume, period)
    return (volume / avg.replace(0, np.nan)).fillna(1.0)


def get_all_indicators(df: pd.DataFrame) -> dict:
    """
    Compute all indicators from an OHLCV DataFrame and return the latest values.

    df must have columns: open, high, low, close, volume
    Returns empty dict if data is insufficient (<30 rows).
    """
    if df.empty or len(df) < 30:
        return {}

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    rsi = calculate_rsi(close)
    macd_df = calculate_macd(close)
    bb_df = calculate_bollinger_bands(close)
    stoch_df = calculate_stochastic(high, low, close)
    adx_df = calculate_adx(high, low, close)
    atr = calculate_atr(high, low, close)
    vol_sig = calculate_volume_signal(volume)

    sma_20 = calculate_sma(close, 20)
    sma_50 = calculate_sma(close, 50)
    sma_200 = calculate_sma(close, 200) if len(df) >= 200 else pd.Series([None] * len(df), index=close.index)
    ema_12 = calculate_ema(close, 12)
    ema_26 = calculate_ema(close, 26)

    def _safe(series, idx=-1):
        val = series.iloc[idx]
        return None if pd.isna(val) else round(float(val), 4)

    return {
        "current_price": _safe(close),
        "rsi": _safe(rsi),
        "macd": _safe(macd_df["macd"]),
        "macd_signal": _safe(macd_df["signal"]),
        "macd_histogram": _safe(macd_df["histogram"]),
        "bb_upper": _safe(bb_df["upper"]),
        "bb_middle": _safe(bb_df["middle"]),
        "bb_lower": _safe(bb_df["lower"]),
        "bb_pct_b": _safe(bb_df["pct_b"]),
        "stoch_k": _safe(stoch_df["k"]),
        "stoch_d": _safe(stoch_df["d"]),
        "adx": _safe(adx_df["adx"]),
        "plus_di": _safe(adx_df["plus_di"]),
        "minus_di": _safe(adx_df["minus_di"]),
        "atr": _safe(atr),
        "sma_20": _safe(sma_20),
        "sma_50": _safe(sma_50),
        "sma_200": _safe(sma_200),
        "ema_12": _safe(ema_12),
        "ema_26": _safe(ema_26),
        "volume_signal": _safe(vol_sig),
        "price_change_1d": _safe(close.pct_change() * 100),
        "price_change_5d": _safe(close.pct_change(5) * 100) if len(df) >= 5 else None,
        "price_change_20d": _safe(close.pct_change(20) * 100) if len(df) >= 20 else None,
    }

"""
watchdog.py - 24/7 portfolio monitoring loop

Four parallel daemon threads, each on its own interval:
  prices       (default: 5 min)  — price alerts
  technicals   (default: 15 min) — RSI/signal alerts
  portfolio    (default: 60 min) — drift/rebalance alerts
  news         (default: 30 min) — sentiment alerts

Usage:
    from financial_engine.watchdog import start_watchdog, stop_watchdog, get_watchdog_status

    dog = start_watchdog(["RELIANCE.NS", "TCS.NS"])
    ...
    stop_watchdog()

Or from CLI:
    python main.py monitor RELIANCE.NS TCS.NS INFY.NS
"""

import json
import logging
import os
import threading
from datetime import datetime
from typing import Callable, List, Optional

LOG_FILE    = "watchdog.log"
STATUS_FILE = "watchdog_status.json"


# ── Logger setup ───────────────────────────────────────────────────────────────

def _make_logger() -> logging.Logger:
    logger = logging.getLogger("fin_watchdog")
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh  = logging.FileHandler(LOG_FILE)
        fh.setFormatter(fmt)
        ch  = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(asctime)s [WATCHDOG] %(message)s"))
        logger.addHandler(fh)
        logger.addHandler(ch)
        logger.setLevel(logging.INFO)
    return logger


# ── Watchdog class ─────────────────────────────────────────────────────────────

class PortfolioWatchdog:
    """
    Multi-threaded 24/7 portfolio monitor.

    Parameters
    ----------
    tickers                  : list of ticker symbols to monitor
    check_interval_prices    : price-alert check interval in seconds
    check_interval_technicals: RSI/indicator check interval in seconds
    check_interval_portfolio : allocation drift check interval in seconds
    check_interval_news      : news sentiment check interval in seconds
    on_alert                 : optional callback(alert_dict) invoked on each trigger
    """

    def __init__(
        self,
        tickers: List[str],
        check_interval_prices: int      = 300,
        check_interval_technicals: int  = 900,
        check_interval_portfolio: int   = 3600,
        check_interval_news: int        = 1800,
        on_alert: Optional[Callable]    = None,
    ):
        self.tickers   = tickers
        self.intervals = {
            "prices":      check_interval_prices,
            "technicals":  check_interval_technicals,
            "portfolio":   check_interval_portfolio,
            "news":        check_interval_news,
        }
        self.on_alert   = on_alert
        self.logger     = _make_logger()
        self._stop      = threading.Event()
        self._threads: dict = {}
        self._last_check: dict = {}
        self.running    = False
        self.start_time = None
        self.alert_count = 0

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self):
        if self.running:
            self.logger.warning("Watchdog already running — ignoring start()")
            return

        self._stop.clear()
        self.running    = True
        self.start_time = datetime.now().isoformat()

        self.logger.info(
            f"Watchdog started | tickers={self.tickers} | "
            f"intervals={self.intervals}"
        )

        tasks = {
            "prices":     self._check_prices,
            "technicals": self._check_technicals,
            "portfolio":  self._check_portfolio,
            "news":       self._check_news,
        }
        for name, fn in tasks.items():
            t = threading.Thread(
                target=self._loop, args=(name, fn), daemon=True, name=f"watchdog-{name}"
            )
            self._threads[name] = t
            t.start()

        self._save_status()
        self.logger.info("All monitoring threads started")

    def stop(self):
        self.logger.info("Stopping watchdog…")
        self._stop.set()
        self.running = False
        for name, t in self._threads.items():
            t.join(timeout=10)
            self.logger.info(f"Thread '{name}' stopped")
        self._threads = {}
        self._save_status()
        self.logger.info("Watchdog stopped")

    def get_status(self) -> dict:
        return {
            "running":        self.running,
            "start_time":     self.start_time,
            "tickers":        self.tickers,
            "intervals":      self.intervals,
            "last_check":     self._last_check,
            "alert_count":    self.alert_count,
            "threads_active": {n: t.is_alive() for n, t in self._threads.items()},
        }

    # ── Internal loop ─────────────────────────────────────────────────────────

    def _loop(self, name: str, check_fn: Callable):
        interval = self.intervals.get(name, 300)
        self.logger.info(f"[{name}] Monitor started (every {interval}s)")

        while not self._stop.is_set():
            try:
                alerts = check_fn()
                self._last_check[name] = datetime.now().isoformat()
                if alerts:
                    self.alert_count += len(alerts)
                    self.logger.info(f"[{name}] {len(alerts)} alert(s) triggered")
                    if self.on_alert:
                        for a in alerts:
                            self.on_alert(a)
                else:
                    self.logger.debug(f"[{name}] No alerts")
                self._save_status()
            except Exception as exc:
                self.logger.error(f"[{name}] Check failed: {exc}")

            self._stop.wait(timeout=interval)

    # ── Check functions ───────────────────────────────────────────────────────

    def _check_prices(self) -> list:
        from .alert_manager import check_price_alerts
        from .stock_data_fetcher import get_stock_price
        triggered = []
        for ticker in self.tickers:
            data = get_stock_price(ticker)
            if "error" not in data:
                triggered.extend(check_price_alerts(ticker, data.get("current_price", 0)))
        return triggered

    def _check_technicals(self) -> list:
        from .alert_manager import check_rsi_alerts
        from .stock_data_fetcher import get_historical_data
        from .technical_indicators import calculate_rsi
        triggered = []
        for ticker in self.tickers:
            try:
                hist = get_historical_data(ticker, period="1mo")
                if hist.empty or len(hist) < 14:
                    continue
                rsi_val = float(calculate_rsi(hist["close"]).iloc[-1])
                if rsi_val >= 70:
                    self.logger.info(f"[technicals] {ticker} RSI={rsi_val:.1f} — OVERBOUGHT")
                elif rsi_val <= 30:
                    self.logger.info(f"[technicals] {ticker} RSI={rsi_val:.1f} — OVERSOLD")
                triggered.extend(check_rsi_alerts(ticker, rsi_val))
            except Exception as exc:
                self.logger.error(f"[technicals] {ticker}: {exc}")
        return triggered

    def _check_portfolio(self) -> list:
        from .alert_manager import list_alerts
        return [a for a in list_alerts() if a.get("type") == "rebalance_needed"]

    def _check_news(self) -> list:
        from .sentiment_analyzer import get_stock_sentiment
        alerts = []
        for ticker in self.tickers:
            try:
                sent = get_stock_sentiment(ticker, news_count=5)
                score = sent.get("score", 0.0)
                mood  = sent.get("mood", "NEUTRAL")
                if score <= -0.50:
                    self.logger.warning(
                        f"[news] {ticker} very negative sentiment (score={score:.2f}, {mood})"
                    )
                    alerts.append({
                        "type":    "news_alert",
                        "ticker":  ticker,
                        "message": f"Very negative news: {mood} (score={score:.2f})",
                        "triggered_at": datetime.now().isoformat(),
                        "last_trigger_message": sent.get("summary", ""),
                    })
                elif score >= 0.50:
                    self.logger.info(
                        f"[news] {ticker} strong positive sentiment (score={score:.2f}, {mood})"
                    )
            except Exception as exc:
                self.logger.error(f"[news] {ticker}: {exc}")
        return alerts

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save_status(self):
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(
                    {
                        "running":     self.running,
                        "start_time":  self.start_time,
                        "tickers":     self.tickers,
                        "intervals":   self.intervals,
                        "last_check":  self._last_check,
                        "alert_count": self.alert_count,
                        "updated_at":  datetime.now().isoformat(),
                    },
                    f, indent=2,
                )
        except Exception:
            pass


# ── Module-level singleton ─────────────────────────────────────────────────────

_watchdog: Optional[PortfolioWatchdog] = None


def start_watchdog(
    tickers: List[str],
    check_interval_prices: int     = 300,
    check_interval_technicals: int = 900,
    check_interval_portfolio: int  = 3600,
    check_interval_news: int       = 1800,
    on_alert: Optional[Callable]   = None,
) -> PortfolioWatchdog:
    """Start (or restart) the global watchdog instance."""
    global _watchdog
    if _watchdog and _watchdog.running:
        stop_watchdog()

    _watchdog = PortfolioWatchdog(
        tickers=tickers,
        check_interval_prices=check_interval_prices,
        check_interval_technicals=check_interval_technicals,
        check_interval_portfolio=check_interval_portfolio,
        check_interval_news=check_interval_news,
        on_alert=on_alert,
    )
    _watchdog.start()
    return _watchdog


def stop_watchdog():
    """Stop the global watchdog instance."""
    global _watchdog
    if _watchdog:
        _watchdog.stop()
        _watchdog = None


def get_watchdog_status() -> dict:
    """Return status of the global watchdog (or last saved status from file)."""
    if _watchdog:
        return _watchdog.get_status()

    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE) as f:
                status = json.load(f)
            status["running"] = False
            return status
        except Exception:
            pass

    return {"running": False, "message": "No watchdog instance found"}

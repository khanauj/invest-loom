"""
alert_manager.py - Price target, RSI, and risk alert system

Alert types:
  price_target   — price crosses a target level
  stop_loss      — price falls below stop-loss
  rsi_overbought — RSI exceeds threshold (default 70)
  rsi_oversold   — RSI drops below threshold (default 30)
  rebalance_needed — portfolio drift alert
  news_alert     — sentiment-triggered alert
  custom         — user-defined condition

Alerts are persisted to alerts.json.
Email delivery requires SMTP_HOST/SMTP_USER/SMTP_PASS env vars.
"""

import json
import uuid
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import List, Optional

ALERTS_FILE = "alerts.json"

ALERT_TYPES = {
    "price_target":    "Price reaches a target level",
    "stop_loss":       "Price drops below stop-loss",
    "rsi_overbought":  "RSI exceeds threshold (default 70)",
    "rsi_oversold":    "RSI drops below threshold (default 30)",
    "rebalance_needed":"Portfolio drift exceeds threshold",
    "news_alert":      "Significant news sentiment detected",
    "custom":          "User-defined condition",
}


# ── Storage helpers ────────────────────────────────────────────────────────────

def _load_alerts() -> list:
    if not os.path.exists(ALERTS_FILE):
        return []
    try:
        with open(ALERTS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def _save_alerts(alerts: list):
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_alert(
    alert_type: str,
    ticker: str = None,
    target_value: float = None,
    message: str = "",
    direction: str = "above",   # "above" | "below"
    notify_email: str = None,
) -> dict:
    """Create and persist a new alert. Returns the alert dict."""
    if alert_type not in ALERT_TYPES:
        raise ValueError(f"Unknown alert type '{alert_type}'. Valid: {list(ALERT_TYPES)}")

    alert = {
        "id":             str(uuid.uuid4())[:8],
        "type":           alert_type,
        "ticker":         ticker,
        "target_value":   target_value,
        "direction":      direction,
        "message":        message,
        "notify_email":   notify_email,
        "active":         True,
        "triggered":      False,
        "created_at":     datetime.now().isoformat(),
        "triggered_at":   None,
        "trigger_count":  0,
        "last_trigger_message": None,
    }
    alerts = _load_alerts()
    alerts.append(alert)
    _save_alerts(alerts)
    return alert


def list_alerts(active_only: bool = True) -> list:
    """Return all (or only active) alerts."""
    alerts = _load_alerts()
    return [a for a in alerts if a.get("active", True)] if active_only else alerts


def delete_alert(alert_id: str) -> bool:
    """Delete alert by ID. Returns True if found and deleted."""
    alerts = _load_alerts()
    new_alerts = [a for a in alerts if a["id"] != alert_id]
    if len(new_alerts) < len(alerts):
        _save_alerts(new_alerts)
        return True
    return False


def deactivate_alert(alert_id: str) -> bool:
    """Deactivate (soft-delete) an alert."""
    alerts = _load_alerts()
    for a in alerts:
        if a["id"] == alert_id:
            a["active"] = False
            _save_alerts(alerts)
            return True
    return False


# ── Check helpers ──────────────────────────────────────────────────────────────

def _mark_triggered(alert: dict, message: str, alerts_list: list):
    alert["triggered"] = True
    alert["triggered_at"] = datetime.now().isoformat()
    alert["trigger_count"] = alert.get("trigger_count", 0) + 1
    alert["last_trigger_message"] = message
    _save_alerts(alerts_list)


def check_price_alerts(ticker: str, current_price: float) -> List[dict]:
    """Return list of price/stop-loss alerts triggered for ticker."""
    alerts = _load_alerts()
    triggered = []

    for alert in alerts:
        if not alert.get("active") or alert.get("ticker") != ticker:
            continue
        atype  = alert.get("type")
        target = alert.get("target_value")
        direction = alert.get("direction", "above")

        if target is None:
            continue

        hit = False
        msg = ""

        if atype == "price_target":
            if direction == "above" and current_price >= target:
                hit = True; msg = f"{ticker} hit {current_price:.2f} (target ≥ {target:.2f})"
            elif direction == "below" and current_price <= target:
                hit = True; msg = f"{ticker} fell to {current_price:.2f} (target ≤ {target:.2f})"

        elif atype == "stop_loss":
            if current_price <= target:
                hit = True; msg = f"STOP LOSS: {ticker} at {current_price:.2f} (stop = {target:.2f})"

        elif atype == "custom":
            if direction == "above" and current_price >= target:
                hit = True; msg = f"Custom alert: {ticker} at {current_price:.2f} (≥ {target:.2f})"
            elif direction == "below" and current_price <= target:
                hit = True; msg = f"Custom alert: {ticker} at {current_price:.2f} (≤ {target:.2f})"

        if hit:
            _mark_triggered(alert, msg, alerts)
            triggered.append(alert)

    return triggered


def check_rsi_alerts(ticker: str, rsi: float) -> List[dict]:
    """Return RSI-based alerts triggered for ticker."""
    alerts = _load_alerts()
    triggered = []

    for alert in alerts:
        if not alert.get("active") or alert.get("ticker") != ticker:
            continue
        atype = alert.get("type")
        default_threshold = 70 if atype == "rsi_overbought" else 30
        threshold = alert.get("target_value", default_threshold)

        hit = False
        msg = ""

        if atype == "rsi_overbought" and rsi >= threshold:
            hit = True; msg = f"RSI OVERBOUGHT: {ticker} RSI={rsi:.1f} (≥ {threshold})"
        elif atype == "rsi_oversold" and rsi <= threshold:
            hit = True; msg = f"RSI OVERSOLD: {ticker} RSI={rsi:.1f} (≤ {threshold})"

        if hit:
            _mark_triggered(alert, msg, alerts)
            triggered.append(alert)

    return triggered


def check_all_alerts(portfolio_tickers: List[str]) -> List[dict]:
    """Run all alert checks for every ticker in the portfolio."""
    from .stock_data_fetcher import get_stock_price, get_historical_data
    from .technical_indicators import calculate_rsi

    all_triggered = []

    for ticker in portfolio_tickers:
        # Price alerts
        price_data = get_stock_price(ticker)
        if "error" not in price_data:
            triggered = check_price_alerts(ticker, price_data.get("current_price", 0))
            all_triggered.extend(triggered)

        # RSI alerts
        hist = get_historical_data(ticker, period="1mo")
        if not hist.empty and len(hist) >= 14:
            rsi_series = calculate_rsi(hist["close"])
            current_rsi = float(rsi_series.iloc[-1])
            rsi_triggered = check_rsi_alerts(ticker, current_rsi)
            all_triggered.extend(rsi_triggered)

    for alert in all_triggered:
        send_notification(alert)

    return all_triggered


# ── Notification ───────────────────────────────────────────────────────────────

def send_notification(alert: dict, extra_msg: str = ""):
    """Print alert to console; optionally send email."""
    msg = alert.get("last_trigger_message") or alert.get("message") or "Alert triggered"

    border = "=" * 60
    print(f"\n{border}")
    print(f"  *** ALERT TRIGGERED ***")
    print(f"  Type:    {alert.get('type', 'unknown').upper()}")
    print(f"  Ticker:  {alert.get('ticker', 'N/A')}")
    print(f"  Message: {msg}")
    if extra_msg:
        print(f"  Detail:  {extra_msg}")
    print(f"  Time:    {alert.get('triggered_at', '')}")
    print(f"{border}\n")

    if alert.get("notify_email"):
        _send_email_alert(alert, msg)


def _send_email_alert(alert: dict, message: str):
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    if not smtp_host or not smtp_user:
        return  # Email not configured — silently skip

    try:
        body = (
            f"Alert triggered: {message}\n\n"
            f"Alert ID: {alert.get('id')}\n"
            f"Time:     {alert.get('triggered_at')}\n"
            f"Ticker:   {alert.get('ticker', 'N/A')}\n"
        )
        msg = MIMEText(body)
        msg["Subject"] = f"[FinEngine] {alert.get('type','Alert').upper()}: {alert.get('ticker','')}"
        msg["From"] = smtp_user
        msg["To"]   = alert["notify_email"]

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as e:
        print(f"Email alert failed: {e}")

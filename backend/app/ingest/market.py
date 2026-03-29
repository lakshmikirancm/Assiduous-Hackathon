"""Market context via yfinance — community-maintained; verify against primary sources."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import yfinance as yf


@dataclass
class YFinanceSnapshot:
    name: str | None
    sector: str | None
    industry: str | None
    market_cap: float | None
    shares_outstanding: float | None
    trailing_pe: float | None
    total_debt: float | None
    total_cash: float | None
    revenue_ttm: float | None
    net_income_ttm: float | None
    free_cashflow_ttm: float | None
    raw_info_subset: dict[str, Any]
    yfinance_degraded: bool


def _f(info: dict, *keys: str) -> float | None:
    for k in keys:
        v = info.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def _load_info_with_retries(ticker: str, attempts: int = 3) -> dict[str, Any]:
    """yfinance occasionally rate-limits (HTTP 429) or returns empty JSON — degrade gracefully."""
    t = yf.Ticker(ticker)
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            data = dict(t.info or {})
            if data:
                return data
        except Exception as e:
            last_err = e
        time.sleep(0.6 * (i + 1))
    # Fallback: fast_info only (fewer fields)
    try:
        fi = getattr(t, "fast_info", None)
        if fi is not None:
            if hasattr(fi, "items"):
                return dict(fi.items())  # type: ignore[arg-type]
            return dict(fi)
    except Exception as e:
        last_err = e
    _ = last_err
    return {}


def fetch_yfinance_snapshot(ticker: str) -> YFinanceSnapshot:
    t = yf.Ticker(ticker)
    info = _load_info_with_retries(ticker)
    degraded = not bool(info.get("symbol") or info.get("shortName") or info.get("longName"))

    # If `info` came from fast_info merge, numeric keys differ — map what we can
    if degraded:
        try:
            fi = dict(getattr(t, "fast_info", {}) or {})
            info = {**fi, **info}
        except Exception:
            pass

    name = info.get("shortName") or info.get("longName") or info.get("short_name") or ticker
    return YFinanceSnapshot(
        name=name if isinstance(name, str) else str(name),
        sector=info.get("sector"),
        industry=info.get("industry"),
        market_cap=_f(info, "marketCap", "market_cap"),
        shares_outstanding=_f(info, "sharesOutstanding", "shares_outstanding"),
        trailing_pe=_f(info, "trailingPE", "forwardPE", "trailing_pe"),
        total_debt=_f(info, "totalDebt", "total_debt"),
        total_cash=_f(info, "totalCash", "total_cash"),
        revenue_ttm=_f(info, "totalRevenue", "total_revenue"),
        net_income_ttm=_f(info, "netIncomeToCommon", "net_income_to_common"),
        free_cashflow_ttm=_f(info, "freeCashflow", "free_cashflow"),
        raw_info_subset={
            k: info.get(k)
            for k in (
                "quoteType",
                "exchange",
                "currency",
                "website",
                "longBusinessSummary",
            )
            if k in info
        },
        yfinance_degraded=degraded,
    )


def fetch_live_quote(ticker: str) -> dict[str, Any]:
    """Best-effort live/delayed quote for demo — not a guaranteed real-time feed."""
    t = yf.Ticker(ticker)
    fi: dict[str, Any] = {}
    for i in range(3):
        try:
            raw = getattr(t, "fast_info", None)
            if raw is not None:
                fi = dict(raw.items()) if hasattr(raw, "items") else dict(raw)  # type: ignore[arg-type]
            if fi:
                break
        except Exception:
            pass
        time.sleep(0.4 * (i + 1))

    last = fi.get("last_price") or fi.get("lastPrice")
    prev = fi.get("previous_close") or fi.get("previousClose")
    day_high = fi.get("day_high") or fi.get("dayHigh")
    day_low = fi.get("day_low") or fi.get("dayLow")
    vol = fi.get("last_volume") or fi.get("lastVolume")
    currency = fi.get("currency")
    ms = fi.get("market_state") or fi.get("marketState")
    return {
        "price": float(last) if last is not None else None,
        "previous_close": float(prev) if prev is not None else None,
        "day_high": float(day_high) if day_high is not None else None,
        "day_low": float(day_low) if day_low is not None else None,
        "volume": int(vol) if vol is not None else None,
        "currency": currency,
        "market_state": str(ms) if ms is not None else None,
        "as_of_unix": fi.get("last_timestamp") or fi.get("lastTimestamp"),
        "degraded": not bool(fi),
    }

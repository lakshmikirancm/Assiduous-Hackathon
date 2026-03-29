"""Named tools the agent can call — each returns JSON-serializable data."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.financial.scenarios import build_three_scenarios
from app.ingest.market import fetch_live_quote, fetch_yfinance_snapshot
from app.models.company import CompanyProfile


async def tool_load_company_bundle(session: AsyncSession, ticker: str) -> dict[str, Any]:
    ticker = ticker.upper()
    result = await session.execute(
        select(CompanyProfile)
        .options(selectinload(CompanyProfile.snapshots))
        .where(CompanyProfile.ticker == ticker)
    )
    co = result.scalar_one_or_none()
    if not co:
        return {"ok": False, "error": "Company not ingested — run POST /api/companies/{ticker}/ingest first"}
    snap = co.snapshots[-1] if co.snapshots else None
    yf = fetch_yfinance_snapshot(ticker)
    return {
        "ok": True,
        "company_id": co.id,
        "name": co.name,
        "sector": co.sector,
        "snapshot": {
            "revenue_ttm": snap.revenue_ttm if snap else None,
            "net_income_ttm": snap.net_income_ttm if snap else None,
            "total_debt": snap.total_debt if snap else None,
            "cash": snap.cash_and_equivalents if snap else None,
            "shares": snap.shares_outstanding if snap else None,
        },
        "yfinance_fcf_ttm": yf.free_cashflow_ttm,
    }


def tool_run_scenarios(payload: dict[str, Any]) -> dict[str, Any]:
    t = payload["ticker"].upper()
    s = build_three_scenarios(
        ticker=t,
        revenue=payload.get("revenue"),
        net_income=payload.get("net_income"),
        fcf_ttm=payload.get("fcf_ttm"),
        total_debt=payload.get("total_debt"),
        cash=payload.get("cash"),
        shares=payload.get("shares"),
    )
    return json.loads(s.model_dump_json())


def tool_live_quote(ticker: str) -> dict[str, Any]:
    q = fetch_live_quote(ticker)
    q["ticker"] = ticker.upper()
    return q

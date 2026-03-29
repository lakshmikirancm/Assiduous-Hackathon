"""Ingest → transform → validate → persist (idempotent per ticker)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.brand import collect_brand_documents
from app.ingest.brand_hints import PUBLIC_HOME_BY_TICKER
from app.ingest.market import fetch_yfinance_snapshot
from app.ingest.sec_edgar import (
    extract_key_metrics_from_facts,
    facts_json_compact,
    fetch_company_facts_json,
    resolve_cik,
)
from app.models.company import CompanyDocument, CompanyProfile, FinancialSnapshot


async def run_ingest_pipeline(session: AsyncSession, ticker: str) -> tuple[int, list[dict]]:
    ticker = ticker.upper()
    steps: list[dict] = []

    steps.append({"step": "resolve_cik", "status": "started"})
    cik, sec_title = await resolve_cik(ticker)
    steps[-1]["status"] = "ok"
    steps[-1]["cik"] = cik

    steps.append({"step": "sec_company_facts", "status": "started"})
    facts_json = await fetch_company_facts_json(cik)
    sec_metrics = extract_key_metrics_from_facts(facts_json)
    compact = facts_json_compact(facts_json)
    steps[-1]["status"] = "ok"
    steps[-1]["sec_revenue"] = sec_metrics.get("revenue")
    steps[-1]["sec_net_income"] = sec_metrics.get("net_income")

    steps.append({"step": "yfinance_snapshot", "status": "started"})
    yf_snap = fetch_yfinance_snapshot(ticker)
    steps[-1]["status"] = "ok"
    steps[-1]["yf_name"] = yf_snap.name
    steps[-1]["degraded"] = getattr(yf_snap, "yfinance_degraded", False)

    website = (yf_snap.raw_info_subset or {}).get("website")
    if not website:
        website = PUBLIC_HOME_BY_TICKER.get(ticker)
    steps.append({"step": "brand_pages", "status": "started"})
    docs = await collect_brand_documents(website, None)
    steps[-1]["status"] = "ok"
    steps[-1]["pages"] = len(docs)

    # Positioning: first ~800 chars from primary doc
    positioning = ""
    brand_summary = (yf_snap.raw_info_subset or {}).get("longBusinessSummary") or ""
    if brand_summary:
        brand_summary = brand_summary[:4000]
    if docs:
        positioning = docs[0][2][:1500]
    if not brand_summary and docs:
        brand_summary = docs[0][2][:3000]

    urls = [d[1] for d in docs]
    if website:
        urls.insert(0, website)

    result = await session.execute(select(CompanyProfile).where(CompanyProfile.ticker == ticker))
    existing = result.scalar_one_or_none()
    if existing:
        existing.cik = cik
        existing.name = yf_snap.name or sec_title
        existing.sector = yf_snap.sector
        existing.industry = yf_snap.industry
        existing.brand_summary = brand_summary or existing.brand_summary
        existing.positioning_notes = positioning or existing.positioning_notes
        existing.source_urls = json.dumps(urls[:20])
        existing.updated_at = datetime.now(timezone.utc)
        company_id = existing.id
        await session.execute(delete(FinancialSnapshot).where(FinancialSnapshot.company_id == company_id))
        await session.execute(delete(CompanyDocument).where(CompanyDocument.company_id == company_id))
    else:
        p = CompanyProfile(
            ticker=ticker,
            cik=cik,
            name=yf_snap.name or sec_title,
            sector=yf_snap.sector,
            industry=yf_snap.industry,
            brand_summary=brand_summary,
            positioning_notes=positioning,
            source_urls=json.dumps(urls[:20]),
        )
        session.add(p)
        await session.flush()
        company_id = p.id

    # Prefer yfinance for market-style fields; SEC for audit trail of revenue/NI when YF missing
    rev = yf_snap.revenue_ttm or sec_metrics.get("revenue")
    ni = yf_snap.net_income_ttm or sec_metrics.get("net_income")

    snap = FinancialSnapshot(
        company_id=company_id,
        as_of=datetime.now(timezone.utc).date().isoformat(),
        revenue_ttm=rev,
        net_income_ttm=ni,
        total_debt=yf_snap.total_debt,
        cash_and_equivalents=yf_snap.total_cash,
        shares_outstanding=yf_snap.shares_outstanding,
        market_cap=yf_snap.market_cap,
        pe_ratio=yf_snap.trailing_pe,
        raw_facts_json=json.dumps(
            {
                "sec_compact": json.loads(compact) if compact else {},
                "yfinance_subset": yf_snap.raw_info_subset,
            }
        ),
    )
    session.add(snap)

    for title, url, content in docs:
        session.add(
            CompanyDocument(
                company_id=company_id,
                title=title,
                source_url=url,
                content=content,
            )
        )

    await session.commit()
    steps.append({"step": "persist", "status": "ok", "company_id": company_id})
    return company_id, steps

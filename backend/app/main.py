import json
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.models.company  # noqa: F401 — register SQLAlchemy models
import app.models.trace  # noqa: F401

from app.agent.runner import run_analysis
from app.config import settings
from app.database import get_session, init_db
from app.ingest.market import fetch_live_quote
from app.ingest.pipeline import run_ingest_pipeline
from app.ingest.report import generate_html_report
from app.models.company import CompanyProfile, FinancialSnapshot
from app.models.trace import AgentTrace
from app.schemas.api import (
    AgentAnalyzeRequest,
    AgentAnalyzeResponse,
    CompanyOut,
    FinancialSnapshotOut,
    IngestResponse,
    LiveQuoteOut,
)

os.makedirs("data", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Corporate Finance Autopilot",
    version="1.0.0",
    description=(
        "Hackathon demo API: ingest public company data (SEC + market), run scenario DCF, "
        "multi-step agent with traces, optional HTML report. Not investment advice."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "corp-finance-autopilot",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.post("/api/companies/{ticker}/ingest", response_model=IngestResponse)
async def ingest_company(ticker: str, session: AsyncSession = Depends(get_session)):
    try:
        company_id, steps = await run_ingest_pipeline(session, ticker)
        return IngestResponse(ticker=ticker.upper(), status="completed", company_id=company_id, steps=steps)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(502, f"Ingest failed: {e!s}") from e


def _snapshot_out(s: FinancialSnapshot | None) -> FinancialSnapshotOut | None:
    if not s:
        return None
    return FinancialSnapshotOut(
        as_of=s.as_of,
        revenue_ttm=s.revenue_ttm,
        net_income_ttm=s.net_income_ttm,
        total_debt=s.total_debt,
        cash_and_equivalents=s.cash_and_equivalents,
        shares_outstanding=s.shares_outstanding,
        market_cap=s.market_cap,
        pe_ratio=s.pe_ratio,
    )


@app.get("/api/companies/{ticker}", response_model=CompanyOut)
async def get_company(ticker: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(CompanyProfile)
        .options(selectinload(CompanyProfile.snapshots))
        .where(CompanyProfile.ticker == ticker.upper())
    )
    co = result.scalar_one_or_none()
    if not co:
        raise HTTPException(404, "Company not found — ingest first")
    snap = co.snapshots[-1] if co.snapshots else None
    urls: list[str] = []
    if co.source_urls:
        try:
            urls = json.loads(co.source_urls)
        except json.JSONDecodeError:
            urls = []
    return CompanyOut(
        id=co.id,
        ticker=co.ticker,
        cik=co.cik,
        name=co.name,
        sector=co.sector,
        industry=co.industry,
        brand_summary=co.brand_summary,
        positioning_notes=co.positioning_notes,
        source_urls=urls,
        snapshot=_snapshot_out(snap),
    )


@app.get("/api/companies/{ticker}/quote", response_model=LiveQuoteOut)
async def get_quote(ticker: str):
    q = fetch_live_quote(ticker)
    return LiveQuoteOut(
        ticker=ticker.upper(),
        price=q.get("price"),
        currency=q.get("currency"),
        market_state=q.get("market_state"),
        day_high=q.get("day_high"),
        day_low=q.get("day_low"),
        volume=q.get("volume"),
        previous_close=q.get("previous_close"),
        as_of_unix=q.get("as_of_unix"),
    )


@app.post("/api/companies/{ticker}/analyze", response_model=AgentAnalyzeResponse)
async def analyze(
    ticker: str,
    body: AgentAnalyzeRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    inc = True if body is None else body.include_llm_narrative
    try:
        return await run_analysis(session, ticker, inc)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/companies/{ticker}/traces")
async def list_traces(ticker: str, limit: int = 15, session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(CompanyProfile).where(CompanyProfile.ticker == ticker.upper()))
    co = r.scalar_one_or_none()
    if not co:
        raise HTTPException(404, "Company not found")
    tr = await session.execute(
        select(AgentTrace)
        .where(AgentTrace.company_id == co.id)
        .order_by(AgentTrace.id.desc())
        .limit(limit)
    )
    rows = tr.scalars().all()
    return [
        {
            "id": x.id,
            "run_id": x.run_id,
            "step_index": x.step_index,
            "step_type": x.step_type,
            "payload": json.loads(x.payload_json),
            "created_at": x.created_at.isoformat(),
        }
        for x in reversed(rows)
    ]


@app.get("/api/companies/{ticker}/report", response_class=HTMLResponse)
async def get_report(ticker: str, session: AsyncSession = Depends(get_session)):
    """Generate and return an HTML investor memorandum for the company."""
    # Get company profile
    result = await session.execute(
        select(CompanyProfile)
        .options(selectinload(CompanyProfile.snapshots))
        .where(CompanyProfile.ticker == ticker.upper())
    )
    co = result.scalar_one_or_none()
    if not co:
        raise HTTPException(404, "Company not found — ingest first")
    
    snap = co.snapshots[-1] if co.snapshots else None
    urls: list[str] = []
    if co.source_urls:
        try:
            urls = json.loads(co.source_urls)
        except json.JSONDecodeError:
            urls = []
    
    company = CompanyOut(
        id=co.id,
        ticker=co.ticker,
        cik=co.cik,
        name=co.name,
        sector=co.sector,
        industry=co.industry,
        brand_summary=co.brand_summary,
        positioning_notes=co.positioning_notes,
        source_urls=urls,
        snapshot=_snapshot_out(snap),
    )
    
    # Run analysis to get scenarios and advisory
    try:
        analysis = await run_analysis(session, ticker, include_llm_narrative=False)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    
    # Generate HTML report
    html = generate_html_report(company, analysis)
    return html

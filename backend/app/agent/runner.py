"""Multi-step analysis with persisted traces (observable agent)."""

from __future__ import annotations

import json
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import tools as T
from app.config import settings
from app.models.trace import AgentTrace
from app.rag.retrieve import retrieve_snippets
from app.schemas.api import (
    AdvisoryOut,
    AgentAnalyzeResponse,
    ScenarioSetOut,
    TraceStepOut,
)


async def _append_trace(
    session: AsyncSession,
    company_id: int | None,
    run_id: str,
    step_index: int,
    step_type: str,
    payload: dict,
) -> None:
    session.add(
        AgentTrace(
            company_id=company_id,
            run_id=run_id,
            step_index=step_index,
            step_type=step_type,
            payload_json=json.dumps(payload, default=str),
        )
    )
    await session.commit()


def _fallback_advisory(
    ticker: str,
    sector: str | None,
    scenarios: ScenarioSetOut,
) -> AdvisoryOut:
    b, d = scenarios.base.equity_per_share, scenarios.downside.equity_per_share
    gap = ""
    if b is not None and d is not None:
        gap = f" Illustrative |Base−Downside| per-share gap ≈ {abs(b - d):.2f}."
    return AdvisoryOut(
        summary=(
            f"{ticker} ({sector or 'Unknown sector'}): illustrative DCF band from "
            f"ingested public data.{gap} "
            "Model and data uncertainty can be large — verify inputs in filings."
        ),
        options_discussion=[
            "Investment-grade debt or revolver if leverage is low and cash flows "
            "stable (verify with filings).",
            "Equity follow-on or convertible only if dilution and covenant terms "
            "align with strategy — not assessed here.",
            "Strategic M&A or buybacks depend on excess cash and hurdle rates — "
            "requires board-level context.",
        ],
        risks_and_uncertainties=[
            "yfinance and vendor APIs can be delayed, restated, or incomplete — triangulate with SEC filings.",
            "DCF is highly sensitive to WACC and terminal growth — small input changes move outputs materially.",
            "Macro, regulatory, and competitive shocks are not modeled explicitly in this demo.",
        ],
        data_gaps=[
            "Segment margins and working capital dynamics are not fully modeled.",
            "Debt maturity schedule and covenants are not pulled automatically in this version.",
        ],
    )


async def _llm_advisory(
    ticker: str,
    company_name: str | None,
    sector: str | None,
    snippets: list[str],
    scenario_json: str,
) -> AdvisoryOut | None:
    if not settings.openai_api_key:
        return None
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        sys = (
            "You are a corporate finance education assistant. Output JSON only with keys: "
            "summary (string), options_discussion (array of strings), risks_and_uncertainties (array), "
            "data_gaps (array). Never claim certainty. Label estimates. Not investment advice."
        )
        user = (
            f"Company: {company_name or ticker} ({ticker}), sector: {sector}.\n"
            f"Scenario model output (JSON): {scenario_json[:8000]}\n"
            f"Retrieved public text snippets (may be truncated):\n---\n"
            + "\n---\n".join(snippets[:4])
        )
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        return AdvisoryOut(
            summary=str(data.get("summary", "")),
            options_discussion=list(data.get("options_discussion") or []),
            risks_and_uncertainties=list(data.get("risks_and_uncertainties") or []),
            data_gaps=list(data.get("data_gaps") or []),
        )
    except Exception:
        return None


async def run_analysis(
    session: AsyncSession,
    ticker: str,
    include_llm_narrative: bool,
) -> AgentAnalyzeResponse:
    run_id = str(uuid.uuid4())
    ticker = ticker.upper()
    step = 0

    step += 1
    bundle = await T.tool_load_company_bundle(session, ticker)
    await _append_trace(session, bundle.get("company_id"), run_id, step, "tool_load_company_bundle", bundle)
    if not bundle.get("ok"):
        raise ValueError(bundle.get("error", "load failed"))

    company_id = int(bundle["company_id"])
    snap = bundle["snapshot"]
    fcf = bundle.get("yfinance_fcf_ttm")

    step += 1
    rag_q = f"{ticker} revenue strategy risk capital structure {bundle.get('name') or ''}"
    snippets = await retrieve_snippets(session, company_id, rag_q, k=5)
    await _append_trace(
        session,
        company_id,
        run_id,
        step,
        "rag_retrieve",
        {"query": rag_q, "snippets_count": len(snippets)},
    )

    step += 1
    scen_payload = {
        "ticker": ticker,
        "revenue": snap.get("revenue_ttm"),
        "net_income": snap.get("net_income_ttm"),
        "fcf_ttm": fcf,
        "total_debt": snap.get("total_debt"),
        "cash": snap.get("cash"),
        "shares": snap.get("shares"),
    }
    scen_dict = T.tool_run_scenarios(scen_payload)
    scenarios = ScenarioSetOut.model_validate(scen_dict)
    await _append_trace(session, company_id, run_id, step, "tool_run_scenarios", {"keys": list(scen_dict.keys())})

    step += 1
    quote = T.tool_live_quote(ticker)
    await _append_trace(session, company_id, run_id, step, "tool_live_quote", quote)

    advisory: AdvisoryOut
    if include_llm_narrative:
        adv = await _llm_advisory(
            ticker,
            bundle.get("name"),
            bundle.get("sector"),
            snippets,
            json.dumps(scen_dict),
        )
        advisory = adv or _fallback_advisory(ticker, bundle.get("sector"), scenarios)
        step += 1
        await _append_trace(
            session,
            company_id,
            run_id,
            step,
            "advisory_narrative",
            {"source": "openai" if adv else "deterministic_fallback"},
        )
    else:
        advisory = _fallback_advisory(ticker, bundle.get("sector"), scenarios)

    traces_result = await session.execute(
        select(AgentTrace).where(AgentTrace.run_id == run_id).order_by(AgentTrace.step_index)
    )
    rows = traces_result.scalars().all()
    traces = [
        TraceStepOut(
            step_index=r.step_index,
            step_type=r.step_type,
            payload=json.loads(r.payload_json),
        )
        for r in rows
    ]

    return AgentAnalyzeResponse(
        run_id=run_id,
        ticker=ticker,
        traces=traces,
        scenarios=scenarios,
        advisory=advisory,
        rag_snippets_used=snippets[:5],
    )

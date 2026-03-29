from pydantic import BaseModel, Field


class LiveQuoteOut(BaseModel):
    ticker: str
    price: float | None
    currency: str | None
    market_state: str | None
    day_high: float | None
    day_low: float | None
    volume: int | None
    previous_close: float | None
    as_of_unix: int | None
    source: str = "yfinance (delayed; not real-time for all venues)"


class FinancialSnapshotOut(BaseModel):
    as_of: str | None
    revenue_ttm: float | None
    net_income_ttm: float | None
    total_debt: float | None
    cash_and_equivalents: float | None
    shares_outstanding: float | None
    market_cap: float | None
    pe_ratio: float | None


class CompanyOut(BaseModel):
    id: int
    ticker: str
    cik: str | None
    name: str | None
    sector: str | None
    industry: str | None
    brand_summary: str | None
    positioning_notes: str | None
    source_urls: list[str] = Field(default_factory=list)
    snapshot: FinancialSnapshotOut | None
    disclaimer: str = (
        "Educational demo only. Data may be incomplete, estimated, or delayed. "
        "Not investment advice."
    )


class IngestResponse(BaseModel):
    ticker: str
    status: str
    company_id: int
    steps: list[dict]
    disclaimer: str = (
        "Public sources only. Verify figures against primary filings before any decision."
    )


class ScenarioCaseOut(BaseModel):
    name: str
    enterprise_value: float | None
    equity_value: float | None
    equity_per_share: float | None
    assumptions: dict


class ScenarioSetOut(BaseModel):
    ticker: str
    base: ScenarioCaseOut
    upside: ScenarioCaseOut
    downside: ScenarioCaseOut
    formula_notes: list[str]
    limitations: list[str]


class AdvisoryOut(BaseModel):
    summary: str
    options_discussion: list[str]
    risks_and_uncertainties: list[str]
    data_gaps: list[str]
    disclaimer: str = (
        "This is not investment, legal, or tax advice. Strategic options are illustrative scenarios."
    )


class TraceStepOut(BaseModel):
    step_index: int
    step_type: str
    payload: dict


class AgentAnalyzeRequest(BaseModel):
    include_llm_narrative: bool = True


class AgentAnalyzeResponse(BaseModel):
    run_id: str
    ticker: str
    traces: list[TraceStepOut]
    scenarios: ScenarioSetOut
    advisory: AdvisoryOut
    rag_snippets_used: list[str]

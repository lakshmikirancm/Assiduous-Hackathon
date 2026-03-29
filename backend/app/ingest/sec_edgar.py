"""SEC EDGAR public APIs — https://www.sec.gov/os/accessing-edgar-data"""

import json
from typing import Any

import httpx

from app.config import settings


async def fetch_company_tickers_map(client: httpx.AsyncClient) -> dict[str, dict]:
    url = "https://www.sec.gov/files/company_tickers.json"
    r = await client.get(url, headers={"User-Agent": settings.sec_user_agent})
    r.raise_for_status()
    data = r.json()
    # Format: {"0": {"cik_str": ..., "ticker": "MSFT", "title": "..."}, ...}
    return {v["ticker"].upper(): v for v in data.values()}


async def resolve_cik(ticker: str) -> tuple[str, str | None]:
    ticker = ticker.upper()
    async with httpx.AsyncClient(timeout=60.0) as client:
        m = await fetch_company_tickers_map(client)
        row = m.get(ticker)
        if not row:
            raise ValueError(f"Unknown ticker on SEC map: {ticker}")
        cik_int = row["cik_str"]
        cik = str(cik_int).zfill(10)
        title = row.get("title")
        return cik, title


async def fetch_company_facts_json(cik: str) -> dict[str, Any]:
    cik = cik.zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(url, headers={"User-Agent": settings.sec_user_agent})
        r.raise_for_status()
        return r.json()


def _latest_us_gaap_fact(facts: dict, tag: str, units_pref: tuple[str, ...]) -> float | None:
    try:
        us_gaap = facts["facts"]["us-gaap"][tag]
    except KeyError:
        return None
    for u in units_pref:
        arr = us_gaap.get("units", {}).get(u)
        if not arr:
            continue
        # Latest filed annual (10-K) preferred
        sorted_rows = sorted(arr, key=lambda x: x.get("filed", ""), reverse=True)
        for row in sorted_rows:
            if row.get("form") in ("10-K", "10-Q") and row.get("val") is not None:
                return float(row["val"])
        if sorted_rows and sorted_rows[0].get("val") is not None:
            return float(sorted_rows[0]["val"])
    return None


def extract_key_metrics_from_facts(facts_json: dict) -> dict[str, float | None]:
    """Pull a few standardized tags when present; may be None."""
    facts = facts_json.get("facts") or {}
    if "us-gaap" not in facts:
        return {"revenue": None, "net_income": None}
    # Revenue: prefer Revenues then RevenuesFromContractWithCustomerExcludingAssessedTax
    revenue = _latest_us_gaap_fact(
        facts_json,
        "Revenues",
        ("USD", "shares", "pure"),
    )
    if revenue is None:
        revenue = _latest_us_gaap_fact(
            facts_json,
            "RevenuesFromContractWithCustomerExcludingAssessedTax",
            ("USD",),
        )
    ni = _latest_us_gaap_fact(facts_json, "NetIncomeLoss", ("USD",))
    if ni is None:
        ni = _latest_us_gaap_fact(facts_json, "ProfitLoss", ("USD",))
    return {"revenue": revenue, "net_income": ni}


def facts_json_compact(facts_json: dict) -> str:
    """Store a trimmed JSON for audit/debug (not full XBRL explosion)."""
    cik = facts_json.get("cik")
    entity = facts_json.get("entityName")
    keys = list((facts_json.get("facts") or {}).get("us-gaap", {}).keys())[:40]
    return json.dumps({"cik": cik, "entityName": entity, "us_gaap_tag_sample": keys}, indent=2)

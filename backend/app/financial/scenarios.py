"""
Transparent multi-case model: 5-year FCF projection + terminal value.

Not a full three-statement model — documented simplifications for hackathon clarity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.schemas.api import ScenarioCaseOut, ScenarioSetOut


@dataclass
class ModelInputs:
    ticker: str
    revenue: float | None
    net_income: float | None
    fcf: float | None
    shares: float | None
    net_debt: float | None  # debt - cash


def _safe_net_debt(debt: float | None, cash: float | None) -> float | None:
    if debt is None and cash is None:
        return None
    d = float(debt or 0.0)
    c = float(cash or 0.0)
    return d - c


def _derive_base_fcf(inp: ModelInputs) -> float | None:
    if inp.fcf is not None and inp.fcf > 0:
        return float(inp.fcf)
    if inp.net_income is not None and inp.net_income > 0:
        # Rough proxy when FCF missing: NI * 0.85 (illustrative conversion)
        return float(inp.net_income) * 0.85
    return None


def _project_fcf_dcf(
    starting_fcf: float,
    growth_rates: list[float],
    wacc: float,
    terminal_growth: float,
) -> tuple[float, float]:
    """Return (pv_fcf_5y, pv_terminal)."""
    if wacc <= terminal_growth:
        terminal_growth = min(terminal_growth, wacc - 0.002)
    fcf = starting_fcf
    pv = 0.0
    for t, g in enumerate(growth_rates, start=1):
        fcf = fcf * (1.0 + g)
        pv += fcf / (1.0 + wacc) ** t
    fcf_terminal = fcf * (1.0 + terminal_growth)
    tv = fcf_terminal / (wacc - terminal_growth)
    pv_tv = tv / (1.0 + wacc) ** len(growth_rates)
    return pv, pv_tv


def build_three_scenarios(
    ticker: str,
    revenue: float | None,
    net_income: float | None,
    fcf_ttm: float | None,
    total_debt: float | None,
    cash: float | None,
    shares: float | None,
) -> ScenarioSetOut:
    nd = _safe_net_debt(total_debt, cash)
    inp = ModelInputs(
        ticker=ticker,
        revenue=revenue,
        net_income=net_income,
        fcf=fcf_ttm,
        shares=shares,
        net_debt=nd,
    )
    starting = _derive_base_fcf(inp)

    limitations = [
        "FCF may be proxied from net income if yfinance free cash flow is missing.",
        "Single WACC assumption per case; real WACC varies by capital structure and market.",
        "5-year horizon with constant terminal growth — sensitivity to long-run growth is high.",
        "Enterprise value from DCF; equity value adds back cash/debt only at net debt level.",
    ]

    formula_notes = [
        "FCF_t = FCF_{t-1} * (1 + g_t); PV = sum_t FCF_t / (1+WACC)^t",
        "Terminal value = FCF_T * (1 + g_term) / (WACC - g_term); discounted to t=0",
        "Equity value = Enterprise value - Net debt (debt - cash)",
        "Equity per share = Equity value / shares outstanding",
    ]

    if starting is None or starting <= 0 or shares is None or shares <= 0:
        empty = ScenarioCaseOut(
            name="n/a",
            enterprise_value=None,
            equity_value=None,
            equity_per_share=None,
            assumptions={},
        )
        return ScenarioSetOut(
            ticker=ticker,
            base=empty.model_copy(update={"name": "Base"}),
            upside=empty.model_copy(update={"name": "Upside"}),
            downside=empty.model_copy(update={"name": "Downside"}),
            formula_notes=formula_notes,
            limitations=limitations
            + ["Insufficient positive FCF/NI to run DCF — provide manual inputs in a future version."],
        )

    # Base growth from revenue trend if available — else anchor to modest GDP+IT
    base_g = 0.06
    if revenue and revenue > 0 and net_income and net_income > 0:
        margin = net_income / revenue
        base_g = float(np.clip(0.03 + margin * 0.15, 0.02, 0.12))

    cases: dict[str, dict[str, Any]] = {
        "Base": {
            "wacc": 0.09,
            "terminal_growth": 0.025,
            "growth_schedule": [base_g * 0.9, base_g, base_g * 0.95, base_g * 0.9, base_g * 0.85],
        },
        "Upside": {
            "wacc": 0.085,
            "terminal_growth": 0.03,
            "growth_schedule": [g + 0.02 for g in [base_g * 0.9, base_g, base_g * 0.95, base_g * 0.9, base_g * 0.85]],
        },
        "Downside": {
            "wacc": 0.105,
            "terminal_growth": 0.015,
            "growth_schedule": [max(g - 0.035, -0.05) for g in [base_g * 0.9, base_g, base_g * 0.95, base_g * 0.9, base_g * 0.85]],
        },
    }

    out_cases: dict[str, ScenarioCaseOut] = {}
    for name, spec in cases.items():
        pv_fcf, pv_tv = _project_fcf_dcf(
            starting,
            spec["growth_schedule"],
            spec["wacc"],
            spec["terminal_growth"],
        )
        ev = pv_fcf + pv_tv
        net_debt_val = nd if nd is not None else 0.0
        eq = ev - net_debt_val
        eps = eq / shares if shares else None
        out_cases[name] = ScenarioCaseOut(
            name=name,
            enterprise_value=float(ev),
            equity_value=float(eq),
            equity_per_share=float(eps) if eps is not None and not math.isnan(eps) else None,
            assumptions={
                "starting_fcf_ttm": starting,
                "wacc": spec["wacc"],
                "terminal_growth": spec["terminal_growth"],
                "yearly_fcf_growth": spec["growth_schedule"],
                "net_debt_used": net_debt_val,
                "shares_outstanding": shares,
            },
        )

    return ScenarioSetOut(
        ticker=ticker,
        base=out_cases["Base"],
        upside=out_cases["Upside"],
        downside=out_cases["Downside"],
        formula_notes=formula_notes,
        limitations=limitations,
    )

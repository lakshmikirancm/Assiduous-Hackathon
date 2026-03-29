from app.financial.scenarios import build_three_scenarios


def test_dcf_produces_three_cases():
    out = build_three_scenarios(
        ticker="TEST",
        revenue=100.0,
        net_income=20.0,
        fcf_ttm=18.0,
        total_debt=50.0,
        cash=30.0,
        shares=1_000_000_000.0,
    )
    assert out.base.enterprise_value is not None
    assert out.upside.equity_per_share is not None


def test_missing_fcf_still_runs_with_net_income():
    out = build_three_scenarios(
        ticker="TEST",
        revenue=100.0,
        net_income=20.0,
        fcf_ttm=None,
        total_debt=None,
        cash=None,
        shares=1e9,
    )
    assert out.base.name == "Base"

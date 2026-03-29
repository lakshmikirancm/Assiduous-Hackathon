"""Unit tests for SEC facts parsing (no network)."""

from app.ingest.sec_edgar import extract_key_metrics_from_facts, facts_json_compact


def _minimal_facts(revenue_val: float, ni_val: float) -> dict:
    row = {"filed": "2024-01-01", "form": "10-K", "val": revenue_val}
    ni_row = {"filed": "2024-01-01", "form": "10-K", "val": ni_val}
    return {
        "cik": 123456,
        "entityName": "Example Corp",
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [row]}},
                "NetIncomeLoss": {"units": {"USD": [ni_row]}},
            }
        },
    }


def test_extract_key_metrics_happy_path():
    facts = _minimal_facts(1_000_000.0, 100_000.0)
    out = extract_key_metrics_from_facts(facts)
    assert out["revenue"] == 1_000_000.0
    assert out["net_income"] == 100_000.0


def test_extract_key_metrics_missing_us_gaap():
    out = extract_key_metrics_from_facts({})
    assert out["revenue"] is None
    assert out["net_income"] is None


def test_facts_json_compact_roundtrip_shape():
    facts = _minimal_facts(1.0, 2.0)
    compact = facts_json_compact(facts)
    assert "Example Corp" in compact
    assert "Revenues" in compact

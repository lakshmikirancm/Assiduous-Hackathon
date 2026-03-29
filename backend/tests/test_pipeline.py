"""Basic smoke tests for the ingest pipeline."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.pipeline import run_ingest_pipeline


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_pipeline_msft(session: AsyncSession):
    """Smoke test: can we ingest a real ticker (MSFT)?"""
    company_id, steps = await run_ingest_pipeline(session, "MSFT")
    assert company_id > 0
    assert len(steps) > 0
    assert steps[0]["step"] == "resolve_cik"
    assert steps[0]["status"] == "ok"
    # Should have resolved a CIK
    assert steps[0].get("cik") is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_invalid_ticker(session: AsyncSession):
    """Invalid ticker should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown ticker"):
        await run_ingest_pipeline(session, "NOTAREALTICKER999")

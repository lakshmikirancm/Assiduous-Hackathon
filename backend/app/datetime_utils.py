"""Timezone-aware UTC helpers for SQLAlchemy defaults."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

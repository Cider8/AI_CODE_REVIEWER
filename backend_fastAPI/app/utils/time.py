"""Timestamp helper.

`datetime.utcnow()` is deprecated from Python 3.12 on. MongoDB stores every
date as naive UTC, so the replacement has to stay naive too — otherwise
timestamps written now become tz-aware while everything already in the
database is naive, and comparing the two raises TypeError.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Current UTC time as a naive datetime (what MongoDB round-trips)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

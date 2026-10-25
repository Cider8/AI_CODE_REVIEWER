"""Timestamp helper.

`datetime.utcnow()` is deprecated from Python 3.12 on. MongoDB stores every
date as naive UTC, so the replacement has to stay naive too — otherwise
timestamps written now become tz-aware while everything already in the
database is naive, and comparing the two raises TypeError.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Current UTC time as a naive datetime (what MongoDB round-trips).

    Truncated to milliseconds, the precision MongoDB stores: otherwise a create
    response (built from the in-memory object) would show microseconds that a
    later read of the same document no longer has."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return now.replace(microsecond=now.microsecond // 1000 * 1000)

"""Opt-in live smoke tests. Never run by default.

QC_LIVE_GEMINI=1 → one real Gemini review (#8) through the API, against the
throwaway QC database. Costs one model call.
"""

import pytest

from qc_helpers import REVIEW_DETAIL_KEYS


@pytest.mark.live_gemini
async def test_ep08_live_gemini_review_smoke_PDD_4_1_1(client, alice):
    r = await client.post(
        "/api/reviews",
        json={"language": "Python", "originalCode": "def add(a, b):\n    return a + b\n"},
        headers=alice.headers,
        timeout=120,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body.keys()) == REVIEW_DETAIL_KEYS
    assert 0 <= body["overallScore"] <= 100

"""Shared helpers for the QC suite (no app imports at module level except
where noted, so conftest can set env vars first)."""

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from bson import ObjectId

PASSWORD = "Password#1"
NEW_PASSWORD = "NewPass#22"

# PDD §3.1: ISO-8601 UTC without a timezone suffix.
ISO_NAIVE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$")

USER_OUT_KEYS = {"_id", "name", "email", "avatar", "preferredLanguages", "createdAt"}
REVIEW_LIST_ITEM_KEYS = {"_id", "title", "language", "overallScore", "createdAt"}
REVIEW_DETAIL_KEYS = {
    "_id", "userId", "title", "originalCode", "language", "summary", "overallScore",
    "bugs", "securityIssues", "performanceIssues", "improvements", "refactoredCode",
    "complexity", "tags", "createdAt",
}
COLLECTION_OUT_KEYS = {"_id", "userId", "name", "description", "reviewIds", "createdAt"}
CHAT_MESSAGE_KEYS = {"_id", "sessionId", "role", "content", "createdAt"}
CHAT_SESSION_KEYS = {"_id", "reviewId", "userId", "createdAt", "remainingMessagesToday"}
STATS_KEYS = {
    "_id", "userId", "totalReviews", "averageScore", "totalBugsFound",
    "totalSecurityIssuesFound", "scoreHistory", "languageBreakdown",
    "commonWeaknesses", "updatedAt",
}


def unique_email(prefix="qc"):
    return f"{prefix}.{uuid.uuid4().hex[:12]}@example.com"


def random_oid():
    return str(ObjectId())


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def assert_iso_naive(value):
    assert isinstance(value, str) and ISO_NAIVE_RE.match(value), f"bad timestamp {value!r}"


def assert_422_shape(resp, field=None):
    """PDD §2.4: 422 detail is a list of {type, loc, msg} only (no input/ctx)."""
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert isinstance(detail, list) and detail, detail
    for err in detail:
        assert set(err.keys()) == {"type", "loc", "msg"}, err
        assert isinstance(err["loc"], list)
    if field is not None:
        assert any(err["loc"][-1] == field for err in detail), detail
    return detail


def assert_error(resp, status, detail=None):
    assert resp.status_code == status, f"{resp.status_code} {resp.text}"
    body = resp.json()
    assert set(body.keys()) == {"detail"}, body
    if detail is not None:
        assert body["detail"] == detail, body
    return body["detail"]


def valid_review_json(**overrides):
    data = {
        "summary": "Correct overall, but has an off-by-one bug.",
        "overall_score": 78,
        "bugs": [
            {"line": 4, "severity": "medium", "category": "Off-by-one error",
             "description": "Loop bound is wrong.", "suggestion": "Use < instead of <=."}
        ],
        "security_issues": [
            {"line": None, "type": "Hardcoded Secret", "description": "Key in source.",
             "fix": "Load it from the environment."}
        ],
        "performance_issues": [
            {"description": "Linear scan.", "suggestion": "Use a set.", "impact": "low"}
        ],
        "improvements": ["Add type hints"],
        "refactored_code": "def bs(a, x):\n    ...",
        "complexity": {"time": "O(log n)", "space": "O(1)"},
        "tags": ["searching", "arrays"],
    }
    data.update(overrides)
    return data


def make_token(sub, *, days=7, extra=None, secret=None):
    """Signs a JWT the way app.utils.security does (imported lazily)."""
    from jose import jwt
    from app.config import settings

    payload = {"sub": sub, "exp": datetime.utcnow() + timedelta(days=days)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret or settings.jwt_secret, algorithm=settings.jwt_algorithm)


@dataclass
class QCUser:
    id: str
    name: str
    email: str
    password: str
    token: str

    @property
    def headers(self):
        return bearer(self.token)


class UserFactory:
    def __init__(self, client):
        self.client = client

    async def create(self, name="QC User", email=None, password=PASSWORD):
        email = email or unique_email(name.lower().replace(" ", ""))
        r = await self.client.post(
            "/api/auth/register", json={"name": name, "email": email, "password": password}
        )
        assert r.status_code == 201, r.text
        body = r.json()
        return QCUser(body["user"]["_id"], name, body["user"]["email"], password, body["token"])


async def create_review(client, user, **body):
    payload = {"title": "Binary Search", "language": "Python", "originalCode": "def bs(a, x): pass"}
    payload.update(body)
    r = await client.post("/api/reviews", json=payload, headers=user.headers)
    assert r.status_code == 201, r.text
    return r.json()


async def create_collection(client, user, name="DSA Practice", description=None):
    r = await client.post(
        "/api/collections", json={"name": name, "description": description}, headers=user.headers
    )
    assert r.status_code == 201, r.text
    return r.json()


async def start_chat(client, user, review_id):
    r = await client.post(f"/api/chat/reviews/{review_id}/start", headers=user.headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── Gemini fake (installed by the autouse fake_gemini fixture) ──────────
class FakeResponse:
    def __init__(self, text=None, text_error=None):
        self._text = text
        self._text_error = text_error

    @property
    def text(self):
        if self._text_error is not None:
            raise self._text_error
        return self._text


class FakeGemini:
    """Stands in for gemini._model. Queue items are consumed one per call:
    a str (reply text), an Exception (raised by the call), a FakeResponse,
    or a callable(contents) -> str. With an empty queue a review prompt (str)
    gets a valid review JSON and a chat call (list) gets a fixed answer."""

    CHAT_ANSWER = "QC fake answer."

    def __init__(self):
        self.queue = []
        self.calls = []

    def push(self, *items):
        self.queue.extend(items)

    async def generate_content_async(self, contents, *args, **kwargs):
        self.calls.append(contents)
        if self.queue:
            item = self.queue.pop(0)
        else:
            item = json.dumps(valid_review_json()) if isinstance(contents, str) else self.CHAT_ANSWER
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, FakeResponse):
            return item
        if callable(item):
            item = item(contents)
        return FakeResponse(item)

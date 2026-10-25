"""#1 GET / and cross-cutting checks (PDD §2.5, §2.6, §3.1)."""

import pytest

import app.database as database
from qc_helpers import assert_error


async def test_ep01_health_returns_welcome_PDD_3_4(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Welcome to KrishnaLens AI Code Review API"}


async def test_ep01_health_works_when_db_down_PDD_2_5(client, monkeypatch):
    monkeypatch.setattr(database, "db_connected", False)
    r = await client.get("/")
    assert r.status_code == 200


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/auth/register"),
        ("POST", "/api/auth/login"),
        ("GET", "/api/auth/me"),
        ("POST", "/api/auth/forgot-password"),
        ("POST", "/api/reviews"),
        ("GET", "/api/reviews"),
        ("GET", "/api/stats"),
        ("GET", "/api/collections"),
        ("POST", "/api/chat/reviews/66fe00000000000000000001/start"),
    ],
)
async def test_db_down_returns_503_PDD_2_5(client, monkeypatch, method, path):
    monkeypatch.setattr(database, "db_connected", False)
    r = await client.request(method, path, json={})
    assert_error(r, 503, "Database unavailable")


async def test_unknown_route_returns_404_PDD_2_4(client):
    r = await client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert "detail" in r.json()


async def test_cors_allows_frontend_origin_only_PDD_2_6(client):
    from app.config import settings

    ok = await client.options(
        "/api/auth/login",
        headers={"Origin": settings.frontend_url, "Access-Control-Request-Method": "POST"},
    )
    assert ok.headers.get("access-control-allow-origin") == settings.frontend_url
    assert ok.headers.get("access-control-allow-credentials") == "true"

    bad = await client.options(
        "/api/auth/login",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in bad.headers


@pytest.mark.live_render
async def test_ep01_render_smoke_get_only_PDD_4_3():
    """Read-only GET against the deployment. Never POST/PATCH/DELETE there."""
    import httpx

    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get("https://ai-code-reviewer-mevv.onrender.com/")
    assert r.status_code == 200
    assert r.json() == {"message": "Welcome to KrishnaLens AI Code Review API"}

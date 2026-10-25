"""Auth guard on every 🔒 endpoint (#4–#21): PDD §2.1, §3.1, §6.3; PR-SIGN-04.

Each case uses a valid body and a well-formed (random) ObjectId so that only
the token decides the outcome.
"""

import pytest

from qc_helpers import assert_422_shape, assert_error, bearer, make_token, random_oid

OID = "66fe00000000000000000001"

PROTECTED = [
    ("ep04", "GET", "/api/auth/me", None),
    ("ep05", "PATCH", "/api/auth/profile", {"name": "X"}),
    ("ep06", "PATCH", "/api/auth/password", {"currentPassword": "Password#1", "newPassword": "NewPass#22"}),
    ("ep07", "DELETE", "/api/auth/account", None),
    ("ep08", "POST", "/api/reviews", {"language": "Python", "originalCode": "x"}),
    ("ep09", "GET", "/api/reviews", None),
    ("ep10", "GET", f"/api/reviews/{OID}", None),
    ("ep11", "DELETE", f"/api/reviews/{OID}", None),
    ("ep12", "GET", "/api/stats", None),
    ("ep13", "POST", "/api/collections", {"name": "C"}),
    ("ep14", "GET", "/api/collections", None),
    ("ep15", "PATCH", f"/api/collections/{OID}", {"name": "C"}),
    ("ep16", "PATCH", f"/api/collections/{OID}/add-review", {"reviewId": OID}),
    ("ep17", "PATCH", f"/api/collections/{OID}/remove-review", {"reviewId": OID}),
    ("ep18", "DELETE", f"/api/collections/{OID}", None),
    ("ep19", "POST", f"/api/chat/reviews/{OID}/start", None),
    ("ep20", "GET", f"/api/chat/sessions/{OID}/messages", None),
    ("ep21", "POST", f"/api/chat/sessions/{OID}/messages", {"content": "hi"}),
]
IDS = [p[0] for p in PROTECTED]


async def _call(client, method, path, body, headers):
    return await client.request(method, path, json=body, headers=headers or {})


@pytest.mark.parametrize("ep,method,path,body", PROTECTED, ids=IDS)
async def test_guard_missing_token_401_not_403_PDD_2_1(client, ep, method, path, body):
    r = await _call(client, method, path, body, None)
    assert_error(r, 401, "Not authenticated")


@pytest.mark.parametrize("ep,method,path,body", PROTECTED, ids=IDS)
async def test_guard_non_bearer_scheme_401_PDD_6_3(client, alice, ep, method, path, body):
    r = await _call(client, method, path, body, {"Authorization": f"Basic {alice.token}"})
    assert_error(r, 401, "Not authenticated")


@pytest.mark.parametrize("ep,method,path,body", PROTECTED, ids=IDS)
async def test_guard_garbage_token_401_PDD_6_3(client, ep, method, path, body):
    r = await _call(client, method, path, body, bearer("not.a.jwt"))
    assert_error(r, 401, "Token invalid or expired")


@pytest.mark.parametrize("ep,method,path,body", PROTECTED, ids=IDS)
async def test_guard_expired_token_401_PR_SIGN_03_PDD_6_3(client, alice, ep, method, path, body):
    r = await _call(client, method, path, body, bearer(make_token(alice.id, days=-1)))
    assert_error(r, 401, "Token invalid or expired")


@pytest.mark.parametrize("ep,method,path,body", PROTECTED, ids=IDS)
async def test_guard_wrong_signature_401_PDD_6_3(client, alice, ep, method, path, body):
    r = await _call(client, method, path, body, bearer(make_token(alice.id, secret="not-the-secret")))
    assert_error(r, 401, "Token invalid or expired")


@pytest.mark.parametrize("ep,method,path,body", PROTECTED, ids=IDS)
async def test_guard_sub_not_objectid_401_PDD_2_1(client, ep, method, path, body):
    r = await _call(client, method, path, body, bearer(make_token("not-an-objectid")))
    assert_error(r, 401, "Token invalid or expired")


@pytest.mark.parametrize("ep,method,path,body", PROTECTED, ids=IDS)
async def test_guard_user_no_longer_exists_401_PDD_6_3(client, ep, method, path, body):
    r = await _call(client, method, path, body, bearer(make_token(random_oid())))
    assert_error(r, 401, "User not found")


@pytest.mark.parametrize("ep,method,path,body", PROTECTED, ids=IDS)
async def test_guard_reset_token_used_as_login_401_PDD_3_5_ep23(client, alice, ep, method, path, body):
    reset_token = make_token(alice.id, extra={"rid": random_oid(), "purpose": "password_reset"})
    r = await _call(client, method, path, body, bearer(reset_token))
    assert_error(r, 401, "Token invalid or expired")


PATH_OID_ENDPOINTS = [
    ("ep10", "GET", "/api/reviews/{}", None),
    ("ep11", "DELETE", "/api/reviews/{}", None),
    ("ep15", "PATCH", "/api/collections/{}", {"name": "C"}),
    ("ep16", "PATCH", "/api/collections/{}/add-review", {"reviewId": OID}),
    ("ep17", "PATCH", "/api/collections/{}/remove-review", {"reviewId": OID}),
    ("ep18", "DELETE", "/api/collections/{}", None),
    ("ep19", "POST", "/api/chat/reviews/{}/start", None),
    ("ep20", "GET", "/api/chat/sessions/{}/messages", None),
    ("ep21", "POST", "/api/chat/sessions/{}/messages", {"content": "hi"}),
]


@pytest.mark.parametrize("ep,method,path,body", PATH_OID_ENDPOINTS, ids=[p[0] for p in PATH_OID_ENDPOINTS])
@pytest.mark.parametrize("bad_id", ["123", "zzzzzzzzzzzzzzzzzzzzzzzz"])
async def test_path_objectid_not_24_hex_422_PDD_3_1(client, alice, ep, method, path, body, bad_id):
    r = await _call(client, method, path.format(bad_id), body, alice.headers)
    assert_422_shape(r)
    assert bad_id not in r.text


async def test_unauthenticated_invalid_body_401_before_422_PDD_1_6(client):
    """PDD v1.4 §1.6: on 🔒 routes get_current_user runs before body validation."""
    r = await client.post("/api/reviews", json={"language": "Python", "originalCode": ""})
    assert_error(r, 401, "Not authenticated")


async def test_authenticated_invalid_body_422_PDD_1_6(client, alice):
    r = await client.post("/api/reviews", json={"language": "Python", "originalCode": ""}, headers=alice.headers)
    assert_422_shape(r, "originalCode")

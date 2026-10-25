"""QC harness for the KrishnaLens backend.

Data safety (see the QC role rules):
- Every run uses its own throwaway database, DB_NAME=krishnalens_qc_<suffix>,
  on the cluster from backend_fastAPI/.env. It is dropped at the end of the
  session, and nothing is ever dropped unless its name starts with
  "krishnalens_qc_".
- EMAIL_PROVIDER=log, so reset codes are only printed (and captured here).
- Gemini is replaced by FakeGemini unless a test is marked live_gemini and
  QC_LIVE_GEMINI=1 is set.

Env vars are set BEFORE anything under app/ is imported, because
app.config.Settings() is evaluated at import time.
"""

import json
import os
import re
import sys
import uuid
from pathlib import Path

import pytest

QC_DIR = Path(__file__).resolve().parent
BACKEND_DIR = QC_DIR.parent / "backend_fastAPI"
QC_DB_PREFIX = "krishnalens_qc_"

# ── Environment, before any app import ───────────────────────────────────
QC_DB_NAME = f"{QC_DB_PREFIX}{uuid.uuid4().hex[:10]}"
os.environ["DB_NAME"] = QC_DB_NAME
os.environ["EMAIL_PROVIDER"] = "log"
# Make sure no real-provider settings leak in from a shell environment.
for _var in ("BREVO_API_KEY", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD"):
    os.environ[_var] = ""
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(QC_DIR))

from app.config import settings  # noqa: E402

if not settings.db_name.startswith(QC_DB_PREFIX):
    pytest.exit(f"Refusing to run: DB_NAME resolved to {settings.db_name!r}", returncode=3)
if settings.email_provider != "log":
    pytest.exit("Refusing to run: EMAIL_PROVIDER is not 'log'", returncode=3)

import app.database as database  # noqa: E402
import app.utils.gemini as gemini  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from qc_helpers import FakeGemini  # noqa: E402

LIVE_GEMINI = os.environ.get("QC_LIVE_GEMINI") == "1"
LIVE_RENDER = os.environ.get("QC_LIVE_RENDER") == "1"


def pytest_collection_modifyitems(config, items):
    skip_gemini = pytest.mark.skip(reason="opt-in: set QC_LIVE_GEMINI=1")
    skip_render = pytest.mark.skip(reason="opt-in: set QC_LIVE_RENDER=1")
    for item in items:
        if "live_gemini" in item.keywords and not LIVE_GEMINI:
            item.add_marker(skip_gemini)
        if "live_render" in item.keywords and not LIVE_RENDER:
            item.add_marker(skip_render)


def pytest_report_header(config):
    return [f"QC database: {QC_DB_NAME} (dropped at session end)", "EMAIL_PROVIDER=log, Gemini mocked"]


# ── Database lifecycle ───────────────────────────────────────────────────
DROP_RESULT = {"dropped": False}


@pytest.fixture(scope="session")
async def qc_db():
    await database.init_db()
    db = database._client[settings.db_name]
    assert db.name == QC_DB_NAME and db.name.startswith(QC_DB_PREFIX)
    try:
        yield db
    finally:
        client = database._client
        if client is not None and QC_DB_NAME.startswith(QC_DB_PREFIX):
            await client.drop_database(QC_DB_NAME)
            names = await client.list_database_names()
            DROP_RESULT["dropped"] = QC_DB_NAME not in names
        await database.close_db()


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_line(
        f"QC database {QC_DB_NAME} dropped: {'yes' if DROP_RESULT['dropped'] else 'NO'}"
    )


@pytest.fixture(scope="session")
async def client(qc_db):
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://qc.test"
    ) as c:
        yield c


# ── Gemini fake ──────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def fake_gemini(request, monkeypatch):
    if "live_gemini" in request.keywords and LIVE_GEMINI:
        yield None
        return
    fake = FakeGemini()
    monkeypatch.setattr(gemini, "_model", fake)
    yield fake


# ── Email capture (EMAIL_PROVIDER=log prints the message) ────────────────
_CODE_RE = re.compile(r"\[email:log\] to=(\S+) .*?reset code is: (\d{6})", re.S)


class Outbox:
    def __init__(self, capsys):
        self._capsys = capsys
        self.sent = []  # (to, code)

    def read(self):
        out = self._capsys.readouterr().out
        found = _CODE_RE.findall(out)
        self.sent.extend(found)
        return found

    def last_code_for(self, email):
        self.read()
        for to, code in reversed(self.sent):
            if to == email:
                return code
        return None


@pytest.fixture
def outbox(capsys):
    return Outbox(capsys)


# ── Users ────────────────────────────────────────────────────────────────
from qc_helpers import UserFactory  # noqa: E402


@pytest.fixture
def users(client):
    return UserFactory(client)


@pytest.fixture
async def alice(users):
    return await users.create("Alice")


@pytest.fixture
async def bob(users):
    return await users.create("Bob")

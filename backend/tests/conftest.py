"""Fixtures compartidas para la suite de tests de MisFacturas v2 (Supabase)."""

import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Test constants ──────────────────────────────────────────────────────────
TEST_USER_ID    = "00000000-0000-0000-0000-000000000001"
TEST_USER_ID_B  = "00000000-0000-0000-0000-000000000002"
TEST_USER_EMAIL = "test@example.com"
TEST_USER       = {"id": TEST_USER_ID, "email": TEST_USER_EMAIL, "user_metadata": {}}
TEST_USER_B     = {"id": TEST_USER_ID_B, "email": "other@example.com", "user_metadata": {}}


# ── In-memory Supabase fake ─────────────────────────────────────────────────

class _FakeTable:
    """Chainable fake Supabase table that operates on a shared list."""

    def __init__(self, store: list):
        self._store = store
        self._filters: list = []
        self._op = None
        self._payload = None
        self._is_single = False
        self._limit_n = None
        self._order_col = None
        self._order_desc = False
        self._selected_cols = None

    # Chain methods
    def select(self, *a):    self._selected_cols = a; return self
    def order(self, col, **kw): self._order_col = col; self._order_desc = kw.get('desc', False); return self
    def limit(self, n):       self._limit_n = n; return self
    def single(self):         self._is_single = True; return self
    def eq(self, col, val):   self._filters.append(('eq', col, str(val))); return self
    def neq(self, col, val):  self._filters.append(('neq', col, str(val))); return self
    def ilike(self, col, val): self._filters.append(('ilike', col, str(val).lower())); return self

    @property
    def not_(self):           return _NotChain(self)

    def insert(self, data):
        self._op = 'insert'
        self._payload = data if isinstance(data, list) else [data]
        return self

    def update(self, data):
        self._op = 'update'
        self._payload = data
        return self

    def delete(self):
        self._op = 'delete'
        return self

    def execute(self):
        result = MagicMock()
        rows = self._apply_filters()

        if self._op == 'insert':
            enriched = []
            for row in self._payload:
                r = dict(row)
                if 'id' not in r:
                    r['id'] = str(uuid.uuid4())
                if 'created_at' not in r:
                    r['created_at'] = datetime.now(timezone.utc).isoformat()
                if 'updated_at' not in r:
                    r['updated_at'] = r['created_at']
                self._store.append(r)
                enriched.append(r)
            result.data = enriched

        elif self._op == 'update':
            for row in rows:
                row.update(self._payload)
            result.data = rows

        elif self._op == 'delete':
            for row in rows:
                if row in self._store:
                    self._store.remove(row)
            result.data = rows

        else:  # select
            if self._order_col:
                rows.sort(key=lambda r: r.get(self._order_col, ''), reverse=self._order_desc)
            if self._limit_n is not None:
                rows = rows[:self._limit_n]
            if self._is_single:
                result.data = rows[0] if rows else None
            else:
                result.data = rows

        return result

    def _apply_filters(self):
        result = list(self._store)
        for op, col, val in self._filters:
            if op == 'eq':
                result = [r for r in result if str(r.get(col, '')) == val]
            elif op == 'neq':
                result = [r for r in result if str(r.get(col, '')) != val]
            elif op == 'ilike':
                result = [r for r in result if str(r.get(col, '')).lower() == val]
            elif op == 'not_is_null':
                result = [r for r in result if r.get(col) is not None]
        return result


class _NotChain:
    def __init__(self, table): self._table = table
    def is_(self, col, val):
        if val == 'null':
            self._table._filters.append(('not_is_null', col, None))
        return self._table


class FakeSupabase:
    """Fake Supabase client with shared in-memory stores per test."""

    def __init__(self):
        self._stores: dict[str, list] = {}
        self.auth = MagicMock()
        self._setup_default_auth()

    def _setup_default_auth(self, user_dict=None):
        u = user_dict or TEST_USER
        mock_resp = MagicMock()
        mock_resp.user.id    = u["id"]
        mock_resp.user.email = u["email"]
        mock_resp.user.user_metadata = u.get("user_metadata", {})
        self.auth.get_user.return_value = mock_resp

    def set_auth_invalid(self):
        mock_resp = MagicMock()
        mock_resp.user = None
        self.auth.get_user.return_value = mock_resp

    def table(self, name: str) -> _FakeTable:
        if name not in self._stores:
            self._stores[name] = []
        return _FakeTable(self._stores[name])

    def seed_bills(self, bills: list):
        self._stores.setdefault('bills', []).extend(bills)

    def seed_profiles(self, profiles: list):
        self._stores.setdefault('profiles', []).extend(profiles)

    def get_bills(self) -> list:
        return self._stores.get('bills', [])


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_supabase():
    """Provides a fresh FakeSupabase instance per test."""
    return FakeSupabase()


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Set fake Supabase env vars so imports don't fail."""
    monkeypatch.setenv("SUPABASE_URL",        "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-service-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET",  "test-secret-key-32-chars-padding!")
    monkeypatch.setenv("GROQ_API_KEY",         "test-groq-key")
    monkeypatch.setenv("WEBHOOK_URL",          "")
    monkeypatch.setenv("WEBHOOK_SECRET",       "")
    monkeypatch.setenv("DRIVE_FOLDER_ID",      "")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN",   "")
    # Legacy vars (kept for any tests that import storage directly)
    monkeypatch.setenv("DATA_FILE",          str(tmp_path / "bills.json"))
    monkeypatch.setenv("NOTIFICATIONS_LOG",  str(tmp_path / "notifications_log.json"))
    monkeypatch.setenv("DRIVE_CONFIG",       str(tmp_path / "drive_config.json"))
    monkeypatch.setenv("WEBHOOK_LOG",        str(tmp_path / "webhook_log.json"))


@pytest_asyncio.fixture
async def client(isolated_env, fake_supabase):
    """Authenticated test client with mocked Supabase and overridden auth dep."""
    import importlib
    from unittest.mock import patch

    with patch('supabase_client.supabase', fake_supabase):
        import auth
        import notifier
        importlib.reload(auth)      # reload so auth.supabase → fake_supabase
        importlib.reload(notifier)
        import main as main_module
        importlib.reload(main_module)

        # Override auth dependency — all requests authenticated as TEST_USER
        from auth import get_current_user
        main_module.app.dependency_overrides[get_current_user] = lambda: TEST_USER

        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        main_module.app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_no_auth(isolated_env, fake_supabase):
    """Unauthenticated client — auth dependency NOT overridden (uses real JWT check)."""
    import importlib
    from unittest.mock import patch

    with patch('supabase_client.supabase', fake_supabase):
        import auth
        import notifier
        importlib.reload(auth)      # reload so auth.supabase → fake_supabase
        importlib.reload(notifier)
        import main as main_module
        importlib.reload(main_module)

        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, fake_supabase

        main_module.app.dependency_overrides.clear()


@pytest.fixture
def sample_bill():
    today = date.today()
    due = (today + timedelta(days=10)).isoformat()
    return {
        "name": "EPEC Electricidad",
        "category": "electricidad",
        "amount": 15432.50,
        "dueDate": due,
        "notes": "Bimestral",
        "isPaid": False,
        "source": "manual",
    }

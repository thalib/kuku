import json
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from app import config, database


@pytest_asyncio.fixture(autouse=True)
async def _fresh_db():
    config.DB_PATH = ":memory:"
    database._db = None
    await database.init_db()
    yield
    await database.close_db()


@pytest.fixture()
def client():
    from app.main import app
    return TestClient(app)


@pytest_asyncio.fixture()
async def _seed_data():
    from app.services.bank_accounts import create_account
    from app.services.categories import create_category, get_category
    from app.services.rules import create_rule
    from app.database import get_db
    from app.models.bank_accounts import BankAccountCreate
    from app.models.categories import CategoryCreate
    from app.models.rules import RuleCreate

    db = await get_db()
    acc = await create_account(db, BankAccountCreate(
        bank_name="HDFC Bank", account_name="Test Account",
        account_number="11112222", ifsc_code="HDFC0001111",
    ))
    cat = await create_category(db, CategoryCreate(
        name="Test Category", type="Expense", description="test",
    ))
    cursor = await db.execute("SELECT * FROM transaction_categories WHERE is_system = 1 AND type = 'Expense' LIMIT 1")
    expense_cat = dict(await cursor.fetchone())
    rule = await create_rule(db, RuleCreate(
        search_text="TEST NARRATION", match_type="contains",
        category_id=expense_cat["id"], priority=5,
    ))
    return {"account": acc, "category": cat, "rule": rule}


class TestBackupPage:
    def test_page_returns_200(self, client):
        assert client.get("/backup").status_code == 200

    def test_page_has_heading(self, client):
        assert "Backup" in client.get("/backup").text


class TestBackupExport:
    def test_export_returns_json(self, client, _seed_data):
        resp = client.get("/backup/export")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        data = json.loads(resp.text)
        assert data["version"] == 1
        assert "exported_at" in data
        assert len(data["bank_accounts"]) >= 1
        assert data["bank_accounts"][0]["bank_name"] == "HDFC Bank"
        assert len(data["categories"]) >= 1
        assert len(data["rules"]) >= 1
        assert data["rules"][0]["category_name"] is not None
        assert data["rules"][0]["category_type"] is not None

    def test_export_excludes_system_accounts(self, client):
        resp = client.get("/backup/export")
        data = json.loads(resp.text)
        for acc in data["bank_accounts"]:
            assert acc["is_system"] == 0

    def test_export_excludes_system_categories(self, client):
        resp = client.get("/backup/export")
        data = json.loads(resp.text)
        for cat in data["categories"]:
            assert "is_system" not in cat

    def test_export_empty_db(self, client):
        resp = client.get("/backup/export")
        data = json.loads(resp.text)
        assert data["bank_accounts"] == []
        assert data["categories"] == []
        assert data["rules"] == []


class TestBackupImport:
    def test_import_invalid_json(self, client):
        resp = client.post("/backup/import", files={"file": ("bad.json", b"not json", "application/json")})
        assert resp.status_code == 200
        assert "Invalid backup file" in resp.text

    def test_import_wrong_version(self, client):
        payload = json.dumps({"version": 999}).encode()
        resp = client.post("/backup/import", files={"file": ("backup.json", payload, "application/json")})
        assert "Unsupported backup version" in resp.text

    def test_import_creates_records(self, client):
        backup = {
            "version": 1,
            "exported_at": "2026-01-01T00:00:00Z",
            "bank_accounts": [{
                "bank_name": "Imported Bank",
                "account_name": "Imported Account",
                "account_number": "99998888",
                "ifsc_code": "IMPT0000001",
                "branch_name": "Main Branch",
                "notes": "imported",
                "is_active": 1,
                "is_system": 0,
            }],
            "categories": [{
                "name": "Imported Category",
                "type": "Income",
                "description": "imported",
            }],
            "rules": [{
                "search_text": "IMPORT TEXT",
                "match_type": "contains",
                "category_name": "Imported Category",
                "category_type": "Income",
                "priority": 1,
                "applies_to": "both",
            }],
        }
        resp = client.post("/backup/import", files={
            "file": ("backup.json", json.dumps(backup).encode(), "application/json"),
        })
        assert "1" in resp.text
        account_resp = client.get("/banks/accounts").text
        assert "Imported Bank" in account_resp

    def test_import_skips_duplicates(self, client, _seed_data):
        backup = {
            "version": 1,
            "exported_at": "2026-01-01T00:00:00Z",
            "bank_accounts": [{
                "bank_name": "HDFC Bank",
                "account_name": "Test Account",
                "account_number": "11112222",
                "ifsc_code": "HDFC0001111",
                "branch_name": None,
                "notes": None,
                "is_active": 1,
                "is_system": 0,
            }],
            "categories": [{
                "name": "Test Category",
                "type": "Expense",
                "description": "test",
            }],
            "rules": [],
        }
        resp = client.post("/backup/import", files={
            "file": ("backup.json", json.dumps(backup).encode(), "application/json"),
        })
        assert "skipped" in resp.text

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
    from app.services.categories import create_category
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


def _v2_backup(bank_accounts=None, categories=None, rules=None):
    return {
        "version": 2,
        "metadata": {
            "created_at": "2026-01-01T00:00:00Z",
            "created_by": "Kuku",
            "app_version": "1.0",
            "stats": {
                "bank_accounts": len(bank_accounts or []),
                "categories": len(categories or []),
                "rules": len(rules or []),
            },
        },
        "data": {
            "bank_accounts": bank_accounts or [],
            "categories": categories or [],
            "rules": rules or [],
        },
    }


def _analyze(client, backup):
    return client.post("/backup/analyze", files={
        "file": ("backup.json", json.dumps(backup).encode(), "application/json"),
    })


def _import(client, token, sections="all"):
    return client.post("/backup/import", data={"token": token, "sections": sections})


def _extract_token(resp_text):
    import re
    m = re.search(r'name="token"\s+value="([^"]+)"', resp_text)
    return m.group(1) if m else None


class TestBackupPage:
    def test_page_returns_200(self, client):
        assert client.get("/backup").status_code == 200

    def test_page_has_heading(self, client):
        assert "Backup" in client.get("/backup").text

    def test_page_has_export_link(self, client):
        assert "/backup/export" in client.get("/backup").text


class TestBackupExport:
    def test_export_returns_v2_json(self, client, _seed_data):
        resp = client.get("/backup/export")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        data = json.loads(resp.text)
        assert data["version"] == 2
        assert "metadata" in data
        assert data["metadata"]["created_by"] == "Kuku"
        assert "stats" in data["metadata"]
        assert "data" in data

    def test_export_contains_backup_data(self, client, _seed_data):
        resp = client.get("/backup/export")
        data = json.loads(resp.text)
        assert len(data["data"]["bank_accounts"]) >= 1
        assert data["data"]["bank_accounts"][0]["bank_name"] == "HDFC Bank"
        assert len(data["data"]["categories"]) >= 1
        assert len(data["data"]["rules"]) >= 1

    def test_export_stats_match_data(self, client, _seed_data):
        resp = client.get("/backup/export")
        data = json.loads(resp.text)
        assert data["metadata"]["stats"]["bank_accounts"] == len(data["data"]["bank_accounts"])
        assert data["metadata"]["stats"]["categories"] == len(data["data"]["categories"])
        assert data["metadata"]["stats"]["rules"] == len(data["data"]["rules"])

    def test_export_excludes_system_accounts(self, client):
        resp = client.get("/backup/export")
        data = json.loads(resp.text)
        for acc in data["data"]["bank_accounts"]:
            assert acc["is_system"] == 0

    def test_export_excludes_system_categories(self, client):
        resp = client.get("/backup/export")
        data = json.loads(resp.text)
        for cat in data["data"]["categories"]:
            assert "is_system" not in cat

    def test_export_empty_db(self, client):
        resp = client.get("/backup/export")
        data = json.loads(resp.text)
        assert data["data"]["bank_accounts"] == []
        assert data["data"]["categories"] == []
        assert data["data"]["rules"] == []

    def test_rules_reference_categories_by_name(self, client, _seed_data):
        resp = client.get("/backup/export")
        data = json.loads(resp.text)
        for rule in data["data"]["rules"]:
            assert "category_name" in rule
            assert "category_type" in rule


class TestBackupAnalyze:
    def test_analyze_invalid_json(self, client):
        resp = client.post("/backup/analyze", files={"file": ("bad.json", b"not json", "application/json")})
        assert resp.status_code == 200
        assert "Invalid backup file" in resp.text

    def test_analyze_wrong_version(self, client):
        payload = {"version": 999}
        resp = _analyze(client, payload)
        assert "Unsupported backup version" in resp.text

    def test_analyze_new_records(self, client):
        backup = _v2_backup(
            bank_accounts=[{
                "bank_name": "New Bank", "account_name": "New Account",
                "account_number": "12345678", "ifsc_code": "XXXX0000001",
                "branch_name": None, "notes": None, "is_active": 1, "is_system": 0,
            }],
        )
        resp = _analyze(client, backup)
        assert resp.status_code == 200
        assert "token" in resp.text
        assert "New Bank" in resp.text
        assert "New Account" in resp.text
        assert "Import Preview" in resp.text

    def test_analyze_existing_records_shown_as_skip(self, client, _seed_data):
        backup = _v2_backup(
            bank_accounts=[{
                "bank_name": "HDFC Bank", "account_name": "Test Account",
                "account_number": "11112222", "ifsc_code": "HDFC0001111",
                "branch_name": None, "notes": None, "is_active": 1, "is_system": 0,
            }, {
                "bank_name": "New Bank", "account_name": "New Account",
                "account_number": "33334444", "ifsc_code": "NEWB0000001",
                "branch_name": None, "notes": None, "is_active": 1, "is_system": 0,
            }],
        )
        resp = _analyze(client, backup)
        assert "Already exists" in resp.text
        assert "New Bank" in resp.text
        assert "HDFC Bank" in resp.text

    def test_analyze_all_existing_shows_error(self, client, _seed_data):
        backup = _v2_backup(
            bank_accounts=[{
                "bank_name": "HDFC Bank", "account_name": "Test Account",
                "account_number": "11112222", "ifsc_code": "HDFC0001111",
                "branch_name": None, "notes": None, "is_active": 1, "is_system": 0,
            }],
            categories=[{
                "name": "Test Category", "type": "Expense", "description": "test",
            }],
        )
        resp = _analyze(client, backup)
        assert "Nothing to import" in resp.text or "already exist" in resp.text

    def test_analyze_rule_with_missing_category(self, client):
        backup = _v2_backup(
            rules=[{
                "search_text": "ORPHAN RULE", "match_type": "contains",
                "category_name": "Nonexistent", "category_type": "Expense",
                "priority": 1, "applies_to": "both",
            }],
        )
        resp = _analyze(client, backup)
        assert "not found" in resp.text.lower() or "warning" in resp.text.lower()

    def test_analyze_backwards_compatible_v1(self, client):
        backup = {
            "version": 1,
            "exported_at": "2026-01-01T00:00:00Z",
            "bank_accounts": [{
                "bank_name": "V1 Bank", "account_name": "V1 Account",
                "account_number": "55556666", "ifsc_code": "V1000000001",
                "branch_name": None, "notes": None, "is_active": 1, "is_system": 0,
            }],
            "categories": [],
            "rules": [],
        }
        resp = _analyze(client, backup)
        assert "V1 Bank" in resp.text
        assert "V1 Account" in resp.text


class TestBackupImport:
    def test_import_with_invalid_token(self, client):
        resp = _import(client, "invalid_token")
        assert "expired" in resp.text.lower() or "error" in resp.text.lower()

    def test_import_creates_records(self, client):
        backup = _v2_backup(
            bank_accounts=[{
                "bank_name": "Imported Bank", "account_name": "Imported Account",
                "account_number": "99998888", "ifsc_code": "IMPT0000001",
                "branch_name": "Main Branch", "notes": "imported",
                "is_active": 1, "is_system": 0,
            }],
            categories=[{
                "name": "Imported Category", "type": "Income", "description": "imported",
            }],
            rules=[{
                "search_text": "IMPORT TEXT", "match_type": "contains",
                "category_name": "Imported Category", "category_type": "Income",
                "priority": 1, "applies_to": "both",
            }],
        )
        resp = _analyze(client, backup)
        token = _extract_token(resp.text)
        assert token
        resp_import = _import(client, token)
        assert "1" in resp_import.text

        account_resp = client.get("/banks/accounts").text
        assert "Imported Bank" in account_resp

    def test_import_skips_duplicates(self, client, _seed_data):
        backup = _v2_backup(
            bank_accounts=[{
                "bank_name": "HDFC Bank", "account_name": "Test Account",
                "account_number": "11112222", "ifsc_code": "HDFC0001111",
                "branch_name": None, "notes": None,
                "is_active": 1, "is_system": 0,
            }],
            categories=[{
                "name": "Test Category", "type": "Expense", "description": "test",
            }],
        )
        resp = _analyze(client, backup)
        token = _extract_token(resp.text)
        if token:
            resp_import = _import(client, token)
            assert "skipped" in resp_import.text.lower() or "Skipped" in resp_import.text

    def test_import_selective_section(self, client):
        backup = _v2_backup(
            bank_accounts=[{
                "bank_name": "Selective Bank", "account_name": "Selective Account",
                "account_number": "77778888", "ifsc_code": "SEL00000001",
                "branch_name": None, "notes": None,
                "is_active": 1, "is_system": 0,
            }],
            categories=[{
                "name": "Selective Category", "type": "Income", "description": "test",
            }],
        )
        resp = _analyze(client, backup)
        token = _extract_token(resp.text)
        assert token
        resp_import = _import(client, token, sections="accounts")
        assert "Selective Bank" in client.get("/banks/accounts").text
        assert "Selective Category" not in client.get("/banks/categories").text

    def test_import_clears_token_after_use(self, client):
        backup = _v2_backup(
            bank_accounts=[{
                "bank_name": "Once Bank", "account_name": "Once Account",
                "account_number": "11223344", "ifsc_code": "ONCE0000001",
                "branch_name": None, "notes": None,
                "is_active": 1, "is_system": 0,
            }],
        )
        resp = _analyze(client, backup)
        token = _extract_token(resp.text)
        assert token
        _import(client, token)
        resp_second = _import(client, token)
        assert "expired" in resp_second.text.lower() or "error" in resp_second.text.lower()

    def test_roundtrip_export_then_reimport(self, client, _seed_data):
        export_resp = client.get("/backup/export")
        export_data = json.loads(export_resp.text)
        original_account = export_data["data"]["bank_accounts"][0]["bank_name"]
        original_cat_count = export_data["metadata"]["stats"]["categories"]
        original_rule_count = export_data["metadata"]["stats"]["rules"]

        export_data["data"]["bank_accounts"].append({
            "bank_name": "Roundtrip Bank", "account_name": "Roundtrip Account",
            "account_number": "44443333", "ifsc_code": "RTTP0000001",
            "branch_name": None, "notes": None, "is_active": 1, "is_system": 0,
        })
        export_data["metadata"]["stats"]["bank_accounts"] += 1

        analyze_resp = _analyze(client, export_data)
        token = _extract_token(analyze_resp.text)
        assert token
        import_resp = _import(client, token)
        assert "Roundtrip Bank" in client.get("/banks/accounts").text
        assert original_account in client.get("/banks/accounts").text

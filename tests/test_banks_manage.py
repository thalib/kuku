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
async def _seed_account():
    from app.services.bank_accounts import create_account
    from app.database import get_db
    from app.models.bank_accounts import BankAccountCreate
    db = await get_db()
    return await create_account(
        db,
        BankAccountCreate(
            bank_name="HDFC Bank",
            account_name="Kuku Pvt Ltd",
            account_number="1234567890",
            ifsc_code="HDFC0001234",
            branch_name="Anna Nagar",
            notes="Primary operations account",
        ),
    )


class TestBanksManagePage:
    def test_get_returns_200(self, client):
        assert client.get("/banks/manage").status_code == 200

    def test_page_has_bank_accounts_heading(self, client):
        assert "Bank Accounts" in client.get("/banks/manage").text

    def test_page_has_add_button(self, client):
        body = client.get("/banks/manage").text
        assert "Add Bank Account" in body

    def test_empty_state_shown_when_no_accounts(self, client):
        assert "No bank accounts" in client.get("/banks/manage").text


class TestBanksManageAdd:
    def test_form_endpoint_returns_form(self, client):
        resp = client.get("/banks/accounts/form")
        assert resp.status_code == 200
        assert "bank_name" in resp.text
        assert "account_number" in resp.text

    def test_create_account_appends_to_list(self, client):
        payload = {
            "bank_name": "ICICI Bank",
            "account_name": "Kuku Ops",
            "account_number": "9988776655",
            "ifsc_code": "ICIC0009999",
            "branch_name": "",
            "notes": "",
        }
        resp = client.post("/banks/accounts", data=payload)
        assert resp.status_code == 200
        body = resp.text
        assert "Kuku Ops" in body
        assert "ICICI Bank" in body


class TestBanksManageToggle:
    def test_toggle_flips_account_to_inactive(self, client, _seed_account):
        account = _seed_account
        resp = client.patch(f"/banks/accounts/{account['id']}/toggle")
        assert resp.status_code == 200
        assert "Inactive" in resp.text

    def test_toggle_reverses(self, client, _seed_account):
        account = _seed_account
        client.patch(f"/banks/accounts/{account['id']}/toggle")
        resp2 = client.patch(f"/banks/accounts/{account['id']}/toggle")
        assert resp2.status_code == 200
        assert "Active" in resp2.text


class TestBanksManageDelete:
    def test_delete_removes_account(self, client, _seed_account):
        account = _seed_account
        resp = client.delete(f"/banks/accounts/{account['id']}")
        assert resp.status_code in (200, 204)
        body = client.get("/banks/manage").text
        assert account["account_name"] not in body


class TestBanksManageEdit:
    def test_edit_form_endpoint_returns_form(self, client, _seed_account):
        account = _seed_account
        resp = client.get(f"/banks/accounts/{account['id']}/edit")
        assert resp.status_code == 200
        assert f'value="{account["bank_name"]}"' in resp.text
        assert "Edit Bank Account" in resp.text

    def test_update_account_changes_values(self, client, _seed_account):
        account = _seed_account
        payload = {
            "bank_name": "SBI Bank",
            "account_name": "Kuku Holdings",
            "account_number": "1111222233",
            "ifsc_code": "SBIN0000001",
            "branch_name": "T Nagar",
            "notes": "Updated",
        }
        resp = client.post(f"/banks/accounts/{account['id']}/update", data=payload)
        assert resp.status_code == 200
        body = resp.text
        assert "SBI Bank" in body
        assert "Kuku Holdings" in body
        assert "****2233" in body

    def test_update_preserves_idempotent_values(self, client, _seed_account):
        account = _seed_account
        payload = {
            "bank_name": account["bank_name"],
            "account_name": account["account_name"],
            "account_number": account["account_number"],
            "ifsc_code": account["ifsc_code"],
            "branch_name": account["branch_name"] or "",
            "notes": account["notes"] or "",
        }
        resp = client.post(f"/banks/accounts/{account['id']}/update", data=payload)
        assert resp.status_code == 200
        assert account["account_name"] in resp.text


class TestBanksManageList:
    def test_list_shows_seeded_account(self, client, _seed_account):
        body = client.get("/banks/manage").text
        assert "HDFC Bank" in body
        assert "Kuku Pvt Ltd" in body

    def test_list_has_table_structure(self, client, _seed_account):
        body = client.get("/banks/manage").text
        assert "table-sm" in body
        assert "table-hover" in body

    def test_list_has_edit_and_delete_actions(self, client, _seed_account):
        body = client.get("/banks/manage").text
        assert "bi-pencil" in body
        assert "bi-trash" in body
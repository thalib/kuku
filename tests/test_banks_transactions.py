import pytest
import pytest_asyncio
import json
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
    return await create_account(db, BankAccountCreate(
        bank_name="HDFC Bank", account_name="Test Account",
        account_number="1234567890", ifsc_code="HDFC0001234",
        branch_name="Main Branch", notes=None,
    ))


@pytest_asyncio.fixture()
async def _seed_transactions(_seed_account):
    from app.services.transactions import bulk_create_transactions
    from app.database import get_db
    db = await get_db()
    txns = [
        {"txn_date": "2024-04-02", "value_date": "2024-04-02", "narration": "NEFT Credit", "reference": "REF001", "debit": 0, "credit": 18940, "balance": 39534.2},
        {"txn_date": "2024-04-02", "value_date": "2024-04-02", "narration": "TPT Staff Salary", "reference": "REF002", "debit": 12000, "credit": 0, "balance": 27534.2},
        {"txn_date": "2024-04-03", "value_date": "2024-04-03", "narration": "POS Purchase", "reference": "REF003", "debit": 1000, "credit": 0, "balance": 26534.2},
    ]
    await bulk_create_transactions(db, _seed_account["id"], txns)
    return {"account": _seed_account, "txns": txns}


@pytest_asyncio.fixture()
async def _get_txn_ids(_seed_transactions):
    from app.services.transactions import list_transactions
    from app.database import get_db
    db = await get_db()
    txns = await list_transactions(db, _seed_transactions["account"]["id"], 2024, 4)
    return [t["id"] for t in txns]


HDFC_CSV = """Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance
02/04/24,NEFT CR-IBKL01-ASENSAR,00401i7401747171,02/04/24,,18940,39534.2
02/04/24,TPT-STAFF SALARY,0000000512413650,02/04/24,12000,,27534.2
03/04/24,POS Purchase,0000409468042100,03/04/24,1000,,26534.2"""

IDBI_CSV = """Srl,Txn Date,Value Date,Description,Cheque No,CR/DR,CCY,Amount (INR),Balance (INR)
1,01/04/2024 13:59:30,01/04/2024,NEFT Credit, ,Dr.,INR,18940,74706.32
2,02/04/2024 15:54:54,02/04/2024,NEFT-AXIS-RAZORPAY, ,Cr.,INR,4237.25,78943.57
3,03/04/2024 09:33:10,03/04/2024,POS Purchase, ,Dr.,INR,649,84912.69"""


class TestTransactionsPage:
    def test_page_returns_200(self, client, _seed_account):
        assert client.get("/banks/transactions").status_code == 200

    def test_page_has_transactions_heading(self, client, _seed_account):
        assert "Transactions" in client.get("/banks/transactions").text

    def test_page_has_import_button(self, client, _seed_account):
        assert "Import" in client.get("/banks/transactions").text

    def test_page_shows_account_dropdown(self, client, _seed_account):
        body = client.get("/banks/transactions").text
        assert "HDFC Bank" in body

    def test_page_shows_empty_state_when_no_accounts(self, client):
        assert "No active bank accounts" in client.get("/banks/transactions").text

    def test_no_view_button_on_page(self, client, _seed_account):
        body = client.get("/banks/transactions").text
        assert "id=\"btnApply\"" not in body
        assert ">View<" not in body


class TestTransactionsFilters:
    def test_filters_returns_200(self, client, _seed_transactions):
        resp = client.get(f"/banks/transactions/filters?account_id={_seed_transactions['account']['id']}")
        assert resp.status_code == 200
        assert "selFy" in resp.text
        assert "selMonth" in resp.text

    def test_filters_only_show_months_with_data(self, client, _seed_transactions):
        body = client.get(f"/banks/transactions/filters?account_id={_seed_transactions['account']['id']}").text
        assert "APR" in body
        assert "JAN" not in body

    def test_filters_show_no_data_when_no_transactions(self, client, _seed_account):
        body = client.get(f"/banks/transactions/filters?account_id={_seed_account['id']}").text
        assert "No transactions uploaded" in body
        assert "selFy" not in body

    def test_filters_show_available_fy_years_with_data(self, client, _seed_transactions):
        body = client.get(f"/banks/transactions/filters?account_id={_seed_transactions['account']['id']}").text
        assert "2024" in body
        assert "FY 2024" in body

    def test_filters_selected_month_is_respected(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        body = client.get(f"/banks/transactions/filters?account_id={aid}&selected_fy=2024&selected_month=4").text
        assert 'value="4" selected' in body


class TestTransactionsTable:
    def test_table_returns_200(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        resp = client.get(f"/banks/transactions/table?account_id={aid}&fy=2024&month=4")
        assert resp.status_code == 200

    def test_table_shows_transactions(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        body = client.get(f"/banks/transactions/table?account_id={aid}&fy=2024&month=4").text
        assert "NEFT Credit" in body
        assert "TPT Staff Salary" in body

    def test_table_shows_summary(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        body = client.get(f"/banks/transactions/table?account_id={aid}&fy=2024&month=4").text
        assert "Total Debit" in body
        assert "Total Credit" in body

    def test_table_shows_empty_for_no_data(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        body = client.get(f"/banks/transactions/table?account_id={aid}&fy=2025&month=1").text
        assert "No transactions" in body

    def test_table_has_edit_and_delete_buttons(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        body = client.get(f"/banks/transactions/table?account_id={aid}&fy=2024&month=4").text
        assert "bi-pencil" in body
        assert "bi-trash" in body


class TestCSVImport:
    def test_import_form_returns_200(self, client, _seed_account):
        resp = client.get(f"/banks/transactions/import/form?account_id={_seed_account['id']}")
        assert resp.status_code == 200
        assert "file" in resp.text

    def test_hdfc_csv_preview(self, client, _seed_account):
        resp = client.post(
            "/banks/transactions/import/preview",
            data={"account_id": str(_seed_account["id"])},
            files={"file": ("hdfc.csv", HDFC_CSV.encode(), "text/csv")},
        )
        assert resp.status_code == 200
        assert "3 transactions" in resp.text
        assert "NEFT CR" in resp.text

    def test_idbi_csv_preview(self, client, _seed_account):
        resp = client.post(
            "/banks/transactions/import/preview",
            data={"account_id": str(_seed_account["id"])},
            files={"file": ("idbi.csv", IDBI_CSV.encode(), "text/csv")},
        )
        assert resp.status_code == 200
        assert "3 transactions" in resp.text

    def test_confirm_import_saves_transactions(self, client, _seed_account):
        from app.services.transactions import parse_csv_rows
        txns = parse_csv_rows(HDFC_CSV)
        resp = client.post(
            "/banks/transactions/import/confirm",
            data={"account_id": str(_seed_account["id"]), "data": json.dumps(txns)},
        )
        assert resp.status_code == 200
        trigger = json.loads(resp.headers["HX-Trigger"])
        details = trigger["txImported"]
        assert details["fy"] == 2024
        assert details["month"] == 4
        assert details["count"] == 3

        aid = _seed_account["id"]
        body = client.get(f"/banks/transactions/table?account_id={aid}&fy=2024&month=4").text
        assert "NEFT" in body

    def test_preview_invalid_file(self, client, _seed_account):
        resp = client.post(
            "/banks/transactions/import/preview",
            data={"account_id": str(_seed_account["id"])},
            files={"file": ("bad.csv", b"not,csv,data\nonly,one,row", "text/csv")},
        )
        assert resp.status_code == 200
        assert "No valid transactions" in resp.text or "Failed to parse" in resp.text


class TestDuplicateDetection:
    def test_compute_txn_hash_is_deterministic(self):
        from app.services.transactions import compute_txn_hash
        txn = {"txn_date": "2024-04-02", "narration": "NEFT", "reference": "REF001", "debit": 100, "credit": 0}
        assert compute_txn_hash(txn) == compute_txn_hash(txn)

    def test_compute_txn_hash_differs_for_different_txns(self):
        from app.services.transactions import compute_txn_hash
        t1 = {"txn_date": "2024-04-02", "narration": "NEFT", "reference": "REF001", "debit": 100, "credit": 0}
        t2 = {"txn_date": "2024-04-02", "narration": "TPT", "reference": "REF002", "debit": 200, "credit": 0}
        assert compute_txn_hash(t1) != compute_txn_hash(t2)

    async def test_find_existing_txn_hashes_returns_matching(self, _seed_account):
        from app.services.transactions import compute_txn_hash, bulk_create_transactions, find_existing_txn_hashes
        from app.database import get_db
        txns = [{"txn_date": "2024-04-02", "value_date": "2024-04-02", "narration": "Existing", "reference": "R1", "debit": 500, "credit": 0, "balance": 0}]
        db = await get_db()
        await bulk_create_transactions(db, _seed_account["id"], txns)
        hashes = {compute_txn_hash(txns[0])}
        found = await find_existing_txn_hashes(db, _seed_account["id"], hashes)
        assert hashes == found

    def test_preview_shows_no_duplicates_first_import(self, client, _seed_account):
        resp = client.post(
            "/banks/transactions/import/preview",
            data={"account_id": str(_seed_account["id"])},
            files={"file": ("hdfc.csv", HDFC_CSV.encode(), "text/csv")},
        )
        assert resp.status_code == 200
        assert "3 transactions" in resp.text
        assert "already exist" not in resp.text

    async def test_preview_shows_duplicates_on_reimport(self, client, _seed_account):
        from app.services.transactions import parse_csv_rows
        txns = parse_csv_rows(HDFC_CSV)
        client.post(
            "/banks/transactions/import/confirm",
            data={"account_id": str(_seed_account["id"]), "data": json.dumps(txns)},
        )
        resp = client.post(
            "/banks/transactions/import/preview",
            data={"account_id": str(_seed_account["id"])},
            files={"file": ("hdfc.csv", HDFC_CSV.encode(), "text/csv")},
        )
        assert resp.status_code == 200
        assert "3 duplicate" in resp.text

    async def test_confirm_skips_duplicates_on_reimport(self, client, _seed_account):
        from app.services.transactions import parse_csv_rows, list_transactions
        from app.database import get_db
        txns = parse_csv_rows(HDFC_CSV)
        client.post(
            "/banks/transactions/import/confirm",
            data={"account_id": str(_seed_account["id"]), "data": json.dumps(txns)},
        )
        resp = client.post(
            "/banks/transactions/import/confirm",
            data={"account_id": str(_seed_account["id"]), "data": json.dumps(txns)},
        )
        assert resp.status_code == 200
        trigger = json.loads(resp.headers["HX-Trigger"])
        details = trigger["txImported"]
        assert details["count"] == 0
        assert details["skipped"] == 3

        db = await get_db()
        all_txns = await list_transactions(db, _seed_account["id"], 2024, 4)
        assert len(all_txns) == 3


class TestTransactionCRUD:
    def test_edit_form_returns_200(self, client, _seed_transactions, _get_txn_ids):
        tid = _get_txn_ids[0]
        resp = client.get(f"/banks/transactions/{tid}/edit")
        assert resp.status_code == 200
        assert "txn_date" in resp.text

    def test_update_transaction(self, client, _seed_transactions, _get_txn_ids):
        tid = _get_txn_ids[0]
        resp = client.post(f"/banks/transactions/{tid}/update", data={
            "txn_date": "2024-04-02",
            "value_date": "2024-04-02",
            "narration": "Updated narration",
            "reference": "UPD001",
            "debit": "0",
            "credit": "20000",
            "balance": "40000",
        })
        assert resp.status_code == 200
        assert "Updated narration" in resp.text

    def test_delete_transaction(self, client, _seed_transactions, _get_txn_ids):
        tid = _get_txn_ids[0]
        resp = client.delete(f"/banks/transactions/{tid}")
        assert resp.status_code == 200

    def test_cancel_edit_returns_row(self, client, _seed_transactions, _get_txn_ids):
        tid = _get_txn_ids[0]
        resp = client.get(f"/banks/transactions/{tid}/cancel")
        assert resp.status_code == 200
        assert "NEFT Credit" in resp.text


class TestExport:
    def test_export_csv(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        resp = client.get(f"/banks/transactions/export/csv?account_id={aid}&fy=2024&month=4")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "NEFT Credit" in resp.text

    def test_export_xlsx(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        resp = client.get(f"/banks/transactions/export/xlsx?account_id={aid}&fy=2024&month=4")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]

    def test_export_pdf(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        resp = client.get(f"/banks/transactions/export/pdf?account_id={aid}&fy=2024&month=4")
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]


class TestCSVParsing:
    def test_hdfc_format_parse(self):
        from app.services.transactions import parse_csv_rows
        txns = parse_csv_rows(HDFC_CSV)
        assert len(txns) == 3
        assert txns[0]["txn_date"] == "2024-04-02"
        assert txns[0]["credit"] == 18940.0
        assert txns[0]["debit"] == 0.0
        assert txns[1]["debit"] == 12000.0
        assert txns[1]["credit"] == 0.0

    def test_idbi_format_parse(self):
        from app.services.transactions import parse_csv_rows
        txns = parse_csv_rows(IDBI_CSV)
        assert len(txns) == 3
        assert txns[0]["txn_date"] == "2024-04-01"
        assert txns[0]["debit"] == 18940.0
        assert txns[1]["credit"] == 4237.25

    def test_amount_with_commas(self):
        from app.services.transactions import _parse_amount
        assert _parse_amount("1,13,692.65") == 113692.65

class TestTransactionCategories:
    def test_table_shows_category_column(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        body = client.get(f"/banks/transactions/table?account_id={aid}&fy=2024&month=4").text
        assert "Category" in body

    def test_uncategorized_shows_widget(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        body = client.get(f"/banks/transactions/table?account_id={aid}&fy=2024&month=4").text
        assert "kuku-search-select" in body

    async def test_category_patch_updates_and_returns_200(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        from app.services.transactions import list_transactions, list_categories_for_transactions
        from app.database import get_db

        db = await get_db()
        txns = await list_transactions(db, aid, 2024, 4)
        cats = await list_categories_for_transactions(db)
        uncategorized_expense_id = None
        for c in cats:
            if c["name"] == "Uncategorized Expense":
                uncategorized_expense_id = c["id"]
                break
        txn_id = txns[0]["id"]
        resp = client.patch(f"/banks/transactions/{txn_id}/category", data={"category_id": uncategorized_expense_id})
        assert resp.status_code == 200

    def test_category_patch_404_for_nonexistent(self, client):
        resp = client.patch("/banks/transactions/99999/category", data={"category_id": 1})
        assert resp.status_code == 404

    async def test_import_auto_classifies_expense(self, client, _seed_account):
        from app.services.transactions import parse_csv_rows, list_transactions
        from app.database import get_db
        from app.services.categories import list_categories

        txns = parse_csv_rows(HDFC_CSV)
        resp = client.post(
            "/banks/transactions/import/confirm",
            data={"account_id": str(_seed_account["id"]), "data": json.dumps(txns)},
        )
        assert resp.status_code == 200

        db = await get_db()
        txns = await list_transactions(db, _seed_account["id"], 2024, 4)
        cats = await list_categories(db)
        uncategorized = next(c for c in cats if c["name"] == "Uncategorized Expense")
        uncategorized_income = next(c for c in cats if c["name"] == "Uncategorized Income")
        expense_txn = next(t for t in txns if t["debit"] > 0)
        income_txn = next(t for t in txns if t["credit"] > 0)
        assert expense_txn["category_id"] == uncategorized["id"]
        assert income_txn["category_id"] == uncategorized_income["id"]

    def test_transaction_row_shows_ref_below_narration(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        body = client.get(f"/banks/transactions/table?account_id={aid}&fy=2024&month=4").text
        assert "(REF: REF001)" in body
        assert "NEFT Credit" in body

    async def test_empty_ref_shows_no_ref_line(self, client, _seed_account):
        from app.services.transactions import bulk_create_transactions
        from app.database import get_db

        db = await get_db()
        await bulk_create_transactions(db, _seed_account["id"], [
            {"txn_date": "2024-04-01", "value_date": "2024-04-01", "narration": "NoRefTxn", "reference": "", "debit": 0, "credit": 500, "balance": 500},
        ])
        body = client.get(f"/banks/transactions/table?account_id={_seed_account['id']}&fy=2024&month=4").text
        assert "NoRefTxn" in body
        assert "(REF:" not in body

    def test_date_parsing_formats(self):
        from app.services.transactions import _parse_date_str
        from datetime import date
        assert _parse_date_str("02/04/24") == date(2024, 4, 2)
        assert _parse_date_str("01/04/2024 13:59:30") == date(2024, 4, 1)
        assert _parse_date_str("2024-04-12 16:42:38.000") == date(2024, 4, 12)

    def test_format_detection_hdfc(self):
        from app.services.transactions import _detect_format
        headers = "Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance".split(",")
        m = _detect_format(headers)
        assert m["type"] == "dual"
        assert "debit" in m
        assert "credit" in m

    def test_format_detection_idbi(self):
        from app.services.transactions import _detect_format
        headers = "Srl,Txn Date,Value Date,Description,Cheque No,CR/DR,CCY,Amount (INR),Balance (INR)".split(",")
        m = _detect_format(headers)
        assert m["type"] == "single"
        assert "crdr" in m
        assert "amount" in m


class TestBulkDelete:
    def test_bulk_summary_returns_json(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        resp = client.get(f"/banks/transactions/bulk/summary?account_id={aid}&fy=2024&month=4")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        assert data["total_debit"] == 13000.0
        assert data["total_credit"] == 18940.0
        assert "Apr" in data["month_label"]

    async def test_bulk_delete_removes_transactions(self, client, _seed_transactions):
        from app.services.transactions import list_transactions
        from app.database import get_db

        aid = _seed_transactions["account"]["id"]
        resp = client.delete(f"/banks/transactions/bulk/delete?account_id={aid}&fy=2024&month=4")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] == 3

        db = await get_db()
        txns = await list_transactions(db, aid, 2024, 4)
        assert len(txns) == 0

    def test_bulk_delete_empty_month_returns_zero(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        resp = client.delete(f"/banks/transactions/bulk/delete?account_id={aid}&fy=2025&month=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] == 0


class TestRunRules:
    def test_run_rules_returns_json(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        resp = client.post("/banks/transactions/rules/run", data={"account_id": aid, "fy": 2024, "month": 4})
        assert resp.status_code == 200
        data = resp.json()
        assert "updated" in data

    async def test_run_rules_updates_categories(self, client, _seed_transactions):
        aid = _seed_transactions["account"]["id"]
        from app.services.categories import create_category
        from app.services.rules import create_rule
        from app.database import get_db
        from app.models.categories import CategoryCreate
        from app.models.rules import RuleCreate

        db = await get_db()
        cat = await create_category(
            db,
            CategoryCreate(
                name="Rule Test Cat",
                type="Expense",
                description="For run rules test",
            ),
        )
        await create_rule(
            db,
            RuleCreate(
                search_text="NEFT",
                match_type="contains",
                category_id=cat["id"],
                priority=1,
                applies_to="both",
                is_active=True,
            ),
        )
        resp = client.post("/banks/transactions/rules/run", data={"account_id": aid, "fy": 2024, "month": 4})
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] > 0

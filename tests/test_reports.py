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


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest_asyncio.fixture
async def db():
    return await database.get_db()


@pytest_asyncio.fixture
async def db_with_data(db):
    from datetime import date
    now = date.today().isoformat()
    await db.execute("""
        INSERT INTO bank_accounts (bank_name, account_name, account_number, ifsc_code, branch_name)
        VALUES ('HDFC Bank', 'Current', '12345678', 'HDFC0000001', 'Main')
    """)
    await db.execute("SELECT last_insert_rowid()")
    account_id = (await db.execute("SELECT id FROM bank_accounts LIMIT 1"))
    row = await account_id.fetchone()
    acc_id = row["id"]

    await db.execute("""
        INSERT INTO bank_transactions
            (account_id, txn_date, value_date, narration, reference, debit, credit, balance, category_id)
        VALUES (?, '2025-06-15', '2025-06-15', 'Sales', '', 0, 10000, 10000,
            (SELECT id FROM transaction_categories WHERE name = 'Sales Revenue' AND type = 'Income' AND is_system = 1 LIMIT 1))
    """, (acc_id,))
    await db.execute("""
        INSERT INTO bank_transactions
            (account_id, txn_date, value_date, narration, reference, debit, credit, balance, category_id)
        VALUES (?, '2025-07-10', '2025-07-10', 'Rent paid', '', 5000, 0, 5000,
            (SELECT id FROM transaction_categories WHERE name = 'Rent & Lease' AND type = 'Expense' AND is_system = 1 LIMIT 1))
    """, (acc_id,))
    await db.execute("""
        INSERT INTO bank_transactions
            (account_id, txn_date, value_date, narration, reference, debit, credit, balance, category_id)
        VALUES (?, '2025-08-05', '2025-08-05', 'Salary', '', 3000, 0, 2000,
            (SELECT id FROM transaction_categories WHERE name = 'Salaries & Wages' AND type = 'Expense' AND is_system = 1 LIMIT 1))
    """, (acc_id,))
    await db.commit()
    return db


class TestReportRoutes:

    def test_reports_index_redirects(self, client):
        resp = client.get("/reports", follow_redirects=False)
        assert resp.status_code == 302
        assert "/reports/profit-loss" in resp.headers["location"]

    def test_fy_years_empty(self, client):
        resp = client.get("/reports/fy-years")
        assert resp.status_code == 200
        data = resp.json()
        assert "fy_years" in data
        assert len(data["fy_years"]) == 3

    def test_fy_years_with_data(self, client, db_with_data):
        resp = client.get("/reports/fy-years")
        assert resp.status_code == 200
        assert 2025 in resp.json()["fy_years"]

    def test_profit_loss_page_returns_200(self, client):
        assert client.get("/reports/profit-loss").status_code == 200

    def test_balance_sheet_page_returns_200(self, client):
        assert client.get("/reports/balance-sheet").status_code == 200

    def test_cash_flow_page_returns_200(self, client):
        assert client.get("/reports/cash-flow").status_code == 200

    def test_content_requires_fy(self, client):
        for path in ["/reports/profit-loss/content", "/reports/balance-sheet/content", "/reports/cash-flow/content"]:
            resp = client.get(path)
            assert resp.status_code == 422, f"{path} should require fy param"

    def test_profit_loss_content_with_data(self, client, db_with_data):
        resp = client.get("/reports/profit-loss/content?fy=2025")
        assert resp.status_code == 200
        body = resp.text
        assert "Sales Revenue" in body
        assert "Rent" in body
        assert "10,000.00" in body

    def test_profit_loss_content_pdf_link(self, client, db_with_data):
        resp = client.get("/reports/profit-loss/content?fy=2025")
        assert "/reports/profit-loss/pdf?fy=2025" in resp.text

    def test_balance_sheet_content_with_data(self, client, db_with_data):
        resp = client.get("/reports/balance-sheet/content?fy=2025")
        assert resp.status_code == 200
        assert "HDFC" in resp.text
        assert "Cash" in resp.text

    def test_cash_flow_content_with_data(self, client, db_with_data):
        resp = client.get("/reports/cash-flow/content?fy=2025")
        assert resp.status_code == 200
        assert "OPERATING" in resp.text

    def test_profit_loss_empty_fy(self, client):
        resp = client.get("/reports/profit-loss/content?fy=2024")
        assert resp.status_code == 200

    def test_nav_reports_group_present(self, client):
        body = client.get("/reports/profit-loss").text
        assert "REPORTS" in body
        assert "/reports/profit-loss" in body
        assert "/reports/balance-sheet" in body
        assert "/reports/cash-flow" in body


class TestReportService:

    @pytest.mark.asyncio
    async def test_profit_loss_data(self, db_with_data):
        from app.services.reports import get_profit_loss
        data = await get_profit_loss(db_with_data, 2025)
        assert data["fy_start"] == 2025
        assert data["total_income"] == 10000
        assert data["total_expense"] == 8000
        assert data["net_profit"] == 2000
        assert data["is_profit"] is True
        assert len(data["income_categories"]) == 1
        assert len(data["expense_categories"]) == 2

    @pytest.mark.asyncio
    async def test_balance_sheet_data(self, db_with_data):
        from app.services.reports import get_balance_sheet
        data = await get_balance_sheet(db_with_data, 2025)
        assert data["fy_start"] == 2025
        assert data["total_cash_at_bank"] == 2000
        assert data["total_assets"] == 2000

    @pytest.mark.asyncio
    async def test_cash_flow_data(self, db_with_data):
        from app.services.reports import get_cash_flow
        data = await get_cash_flow(db_with_data, 2025)
        assert data["fy_start"] == 2025
        assert data["operating_inflows"] == 10000
        assert data["operating_outflows"] == 8000
        assert data["net_operating"] == 2000

    @pytest.mark.asyncio
    async def test_empty_db_no_crash(self, db):
        from app.services.reports import get_profit_loss, get_balance_sheet, get_cash_flow
        pl = await get_profit_loss(db, 2025)
        assert pl["total_income"] == 0
        bs = await get_balance_sheet(db, 2025)
        assert bs["total_assets"] == 0
        cf = await get_cash_flow(db, 2025)
        assert cf["net_change"] == 0

    @pytest.mark.asyncio
    async def test_cash_flow_derives_opening_from_first_credit_txn(self, db):
        from app.services.reports import get_cash_flow

        await db.execute("""
            INSERT INTO bank_accounts (bank_name, account_name, account_number, ifsc_code, branch_name, is_system)
            VALUES ('HDFC', 'Test', 'X1', 'X1', NULL, 1)
        """)
        row = await (await db.execute(
            "SELECT id FROM bank_accounts WHERE account_name = 'Test'")).fetchone()
        acc_id = row["id"]

        await db.execute("""
            INSERT INTO bank_transactions
                (account_id, txn_date, value_date, narration, reference, debit, credit, balance, category_id)
            VALUES (?, '2025-08-10', '2025-08-10', 'Cash received', '', 0, 100, 9500,
                (SELECT id FROM transaction_categories WHERE name = 'Sales Revenue' AND type = 'Income' AND is_system = 1 LIMIT 1))
        """, (acc_id,))
        await db.commit()

        data = await get_cash_flow(db, 2025)
        assert data["opening_cash"] == 9400.0

    @pytest.mark.asyncio
    async def test_cash_flow_derives_opening_from_first_debit_txn(self, db):
        from app.services.reports import get_cash_flow

        await db.execute("""
            INSERT INTO bank_accounts (bank_name, account_name, account_number, ifsc_code, branch_name, is_system)
            VALUES ('HDFC', 'Test2', 'X2', 'X2', NULL, 1)
        """)
        row = await (await db.execute(
            "SELECT id FROM bank_accounts WHERE account_name = 'Test2'")).fetchone()
        acc_id = row["id"]

        await db.execute("""
            INSERT INTO bank_transactions
                (account_id, txn_date, value_date, narration, reference, debit, credit, balance, category_id)
            VALUES (?, '2025-08-10', '2025-08-10', 'Cash paid', '', 200, 0, 9300,
                (SELECT id FROM transaction_categories WHERE name = 'Rent & Lease' AND type = 'Expense' AND is_system = 1 LIMIT 1))
        """, (acc_id,))
        await db.commit()

        data = await get_cash_flow(db, 2025)
        assert data["opening_cash"] == 9500.0

    @pytest.mark.asyncio
    async def test_cash_flow_opening_uses_prior_balance_when_available(self, db):
        from app.services.reports import get_cash_flow

        await db.execute("""
            INSERT INTO bank_accounts (bank_name, account_name, account_number, ifsc_code, branch_name, is_system)
            VALUES ('HDFC', 'Test3', 'X3', 'X3', NULL, 1)
        """)
        row = await (await db.execute(
            "SELECT id FROM bank_accounts WHERE account_name = 'Test3'")).fetchone()
        acc_id = row["id"]

        await db.execute("""
            INSERT INTO bank_transactions
                (account_id, txn_date, value_date, narration, reference, debit, credit, balance, category_id)
            VALUES (?, '2025-03-15', '2025-03-15', 'Prior year sale', '', 0, 5000, 5000,
                (SELECT id FROM transaction_categories WHERE name = 'Sales Revenue' AND type = 'Income' AND is_system = 1 LIMIT 1))
        """, (acc_id,))
        await db.execute("""
            INSERT INTO bank_transactions
                (account_id, txn_date, value_date, narration, reference, debit, credit, balance, category_id)
            VALUES (?, '2025-08-10', '2025-08-10', 'Cash received', '', 0, 100, 5100,
                (SELECT id FROM transaction_categories WHERE name = 'Sales Revenue' AND type = 'Income' AND is_system = 1 LIMIT 1))
        """, (acc_id,))
        await db.commit()

        data = await get_cash_flow(db, 2025)
        assert data["opening_cash"] == 5000.0

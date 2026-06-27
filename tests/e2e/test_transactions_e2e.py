import json
import re


HDFC_CSV = """Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance
02/04/24,NEFT CR-IBKL01-ASENSAR,00401i7401747171,02/04/24,,18940,39534.2
02/04/24,TPT-STAFF SALARY,0000000512413650,02/04/24,12000,,27534.2
03/04/24,POS Purchase,0000409468042100,03/04/24,1000,,26534.2"""


def create_account(api, bank_name="E2E Txn Bank", account_name="E2E Txn Account",
                   account_number="55556666", ifsc_code="E2TX0000001"):
    import re as _re
    resp = api.post("/banks/accounts", data={
        "bank_name": bank_name,
        "account_name": account_name,
        "account_number": account_number,
        "ifsc_code": ifsc_code,
        "branch_name": "",
        "notes": "",
    })
    ids = _re.findall(r'accounts/(\d+)/toggle', resp.text)
    return ids[0] if ids else None


class TestTransactionsPage:
    def test_page_loads(self, page_goto):
        page = page_goto("/banks/transactions")
        assert "Transactions" in page.locator("h1").text_content()

    def test_shows_account_dropdown_when_account_exists(self, api, page_goto):
        create_account(api, f"TxnPage Bank {id(self)}", f"TxnPage Account {id(self)}",
                       f"{id(self) % 10000:04d}0001", f"TPG{id(self) % 10000:07d}")
        page = page_goto("/banks/transactions")
        assert page.locator("#selAccount").is_visible()

    def test_account_dropdown_contains_account(self, api, page_goto):
        create_account(api, "E2E Dropdown Bank", "E2E Dropdown Account",
                       "77778888", "E2DR0000001")
        page = page_goto("/banks/transactions")
        content = page.content()
        assert "E2E Dropdown Bank" in content


class TestTransactionsFilterAndTable:
    def test_selecting_account_shows_filters(self, api, page_goto):
        aid = create_account(api, "E2E Filter Bank", "E2E Filter Account", "11112222", "E2FL0000001")
        assert aid is not None
        api.post("/banks/transactions/import/confirm", data={
            "account_id": aid,
            "data": json.dumps([
                {"txn_date": "2024-04-02", "value_date": "2024-04-02", "narration": "NEFT Filter Test", "reference": "REFFLT", "debit": 0, "credit": 18940, "balance": 39534.2},
            ]),
        })
        page = page_goto("/banks/transactions")
        page.locator("#selAccount").select_option(aid)
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#selFy", state="visible", timeout=5000)
        assert page.locator("#selFy").is_visible()

    def test_selecting_month_loads_table(self, api, page_goto):
        aid = create_account(api, "E2E Table Bank", "E2E Table Account", "33334444", "E2TB0000001")
        assert aid is not None
        api.post("/banks/transactions/import/confirm", data={
            "account_id": aid,
            "data": json.dumps([
                {"txn_date": "2024-04-02", "value_date": "2024-04-02", "narration": "NEFT E2E Table Test", "reference": "REFTB", "debit": 0, "credit": 5000, "balance": 5000},
            ]),
        })
        page = page_goto("/banks/transactions")
        page.locator("#selAccount").select_option(aid)
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#selFy", state="visible", timeout=5000)
        page.locator("#selFy").select_option("2024")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#selMonth", state="visible", timeout=5000)
        page.locator("#selMonth").select_option("4")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#hx-table-area", timeout=5000)
        content = page.locator("#hx-table-area").inner_html()
        assert "NEFT E2E Table Test" in content


class TestCSVImport:
    def test_import_form_opens_in_modal(self, api, page_goto):
        from app.services.transactions import parse_csv_rows
        aid = create_account(api, "E2E Import Bank", "E2E Import Account", "55557777", "E2IM0000001")
        assert aid is not None
        page = page_goto("/banks/transactions")
        page.locator("#selAccount").select_option(aid)
        page.wait_for_load_state("networkidle")
        page.locator("#btnImport").click()
        page.wait_for_selector("#importModal .modal-body", state="visible", timeout=5000)
        assert page.locator("#importModal").is_visible()

    def test_import_preview_via_api(self, api):
        aid = create_account(api, "E2E Preview Bank", "E2E Preview Account", "88889998", "E2PV0000001")
        assert aid is not None
        resp = api.post(
            "/banks/transactions/import/preview",
            data={"account_id": str(aid)},
            files={"file": ("hdfc.csv", HDFC_CSV.encode(), "text/csv")},
        )
        assert resp.status_code == 200
        assert "3 transactions" in resp.text


class TestTransactionExport:
    def test_export_csv_download(self, api):
        from app.services.transactions import parse_csv_rows
        aid = create_account(api, "E2E Export Bank", "E2E Export Account", "66667779", "E2EX0000001")
        assert aid is not None
        txns = parse_csv_rows(HDFC_CSV)
        api.post("/banks/transactions/import/confirm", data={
            "account_id": aid,
            "data": json.dumps(txns),
        })
        resp = api.get(f"/banks/transactions/export/csv?account_id={aid}&fy=2024&month=4")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "NEFT" in resp.text

    def test_export_xlsx_download(self, api):
        from app.services.transactions import parse_csv_rows
        aid = create_account(api, "E2E XLSX Bank", "E2E XLSX Account", "66667780", "E2XX0000001")
        assert aid is not None
        txns = parse_csv_rows(HDFC_CSV)
        api.post("/banks/transactions/import/confirm", data={
            "account_id": aid,
            "data": json.dumps(txns),
        })
        resp = api.get(f"/banks/transactions/export/xlsx?account_id={aid}&fy=2024&month=4")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]


class TestBulkDelete:
    def test_bulk_summary_endpoint(self, api):
        from app.services.transactions import parse_csv_rows
        aid = create_account(api, "E2E BulkSum Bank", "E2E BulkSum Account", "99990001", "E2BS0000001")
        assert aid is not None
        txns = parse_csv_rows(HDFC_CSV)
        api.post("/banks/transactions/import/confirm", data={
            "account_id": aid,
            "data": json.dumps(txns),
        })
        resp = api.get(f"/banks/transactions/bulk/summary?account_id={aid}&fy=2024&month=4")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3

    def test_bulk_delete_endpoint(self, api):
        from app.services.transactions import parse_csv_rows
        aid = create_account(api, "E2E BulkDel Bank", "E2E BulkDel Account", "99990002", "E2BD0000001")
        assert aid is not None
        txns = parse_csv_rows(HDFC_CSV)
        api.post("/banks/transactions/import/confirm", data={
            "account_id": aid,
            "data": json.dumps(txns),
        })
        resp = api.delete(f"/banks/transactions/bulk/delete?account_id={aid}&fy=2024&month=4")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] == 3

    def test_bulk_delete_empty_returns_zero(self, api):
        aid = create_account(api, "E2E BulkEmpty Bank", "E2E BulkEmpty Account", "99990003", "E2BE0000001")
        assert aid is not None
        resp = api.delete(f"/banks/transactions/bulk/delete?account_id={aid}&fy=2025&month=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] == 0


class TestRunRules:
    def test_run_rules_endpoint(self, api):
        from app.services.transactions import parse_csv_rows
        aid = create_account(api, "E2E Rules Bank", "E2E Rules Account", "99990004", "E2RR0000001")
        assert aid is not None
        txns = parse_csv_rows(HDFC_CSV)
        api.post("/banks/transactions/import/confirm", data={
            "account_id": aid,
            "data": json.dumps(txns),
        })
        resp = api.post("/banks/transactions/rules/run", data={
            "account_id": aid,
            "fy": 2024,
            "month": 4,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "updated" in data

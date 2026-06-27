class TestBankAccountsPage:
    def test_page_loads(self, page_goto):
        page = page_goto("/banks/manage")
        assert "Bank Accounts" in page.locator("h1").text_content()

    def test_add_button_present(self, page_goto):
        page = page_goto("/banks/manage")
        assert page.get_by_text("Add Bank Account").is_visible()

    def test_empty_state_shown(self, page_goto):
        page = page_goto("/banks/manage")
        assert "No bank accounts" in page.content()


class TestBankAccountCreate:
    def test_add_form_opens_on_click(self, page_goto):
        page = page_goto("/banks/manage")
        page.get_by_text("Add Bank Account").click()
        page.wait_for_load_state("networkidle")
        form = page.locator("#account-form-card form")
        assert form.is_visible()
        assert "Bank Name" in page.content()
        assert "Account Number" in page.content()

    def test_create_account_via_api(self, api, page_goto):
        resp = api.post("/banks/accounts", data={
            "bank_name": "E2E Test Bank",
            "account_name": "E2E Account",
            "account_number": "00001111",
            "ifsc_code": "E2ET0000001",
            "branch_name": "",
            "notes": "",
        })
        assert resp.status_code == 200
        page = page_goto("/banks/manage")
        assert "E2E Test Bank" in page.content()
        assert "E2E Account" in page.content()
        assert "****1111" in page.content()

    def test_create_account_via_form(self, page_goto):
        page = page_goto("/banks/manage")
        page.get_by_text("Add Bank Account").click()
        page.wait_for_load_state("networkidle")
        form = page.locator("#account-form-card form")
        form.locator('[name="bank_name"]').fill("Form Bank")
        form.locator('[name="account_name"]').fill("Form Account")
        form.locator('[name="account_number"]').fill("22223333")
        form.locator('[name="ifsc_code"]').fill("FORM0000001")
        form.get_by_text("Save").click()
        page.wait_for_selector("text=Form Bank", timeout=5000)
        assert "Form Bank" in page.content()
        assert "Form Account" in page.content()


class TestBankAccountEdit:
    def test_edit_form_opens(self, page_goto, api):
        api.post("/banks/accounts", data={
            "bank_name": "Edit Test Bank",
            "account_name": "Edit Account",
            "account_number": "44445555",
            "ifsc_code": "EDIT0000001",
            "branch_name": "",
            "notes": "",
        })
        page = page_goto("/banks/manage")
        page.locator('button[hx-get*="/edit"]').first.click()
        page.wait_for_load_state("networkidle")
        form = page.locator("#account-form-card form")
        assert form.is_visible()
        assert "Edit Bank Account" in page.content()

    def test_update_account_via_api(self, api, page_goto):
        resp = api.post("/banks/accounts", data={
            "bank_name": "Update Bank",
            "account_name": "Update Account",
            "account_number": "66667777",
            "ifsc_code": "UPDT0000001",
            "branch_name": "",
            "notes": "",
        })
        import re
        match = re.search(r'data-aid="(\d+)"', resp.text) or re.search(r'accounts/(\d+)/edit', resp.text)
        id_match = re.search(r'toggle/(\d+)|edit/(\d+)', resp.text)
        aid = id_match.group(1) or id_match.group(2) if id_match else "1"

        html = page_goto("/banks/manage").content()
        import re as re2
        m = re2.search(rf'accounts/(\d+)/edit', html)
        if m:
            aid = m.group(1)

        update_resp = api.post(f"/banks/accounts/{aid}/update", data={
            "bank_name": "Updated Bank Name",
            "account_name": "Updated Account Name",
            "account_number": "66667777",
            "ifsc_code": "UPDT0000001",
            "branch_name": "",
            "notes": "",
        })
        assert update_resp.status_code == 200
        page = page_goto("/banks/manage")
        assert "Updated Bank Name" in page.content()


class TestBankAccountToggle:
    def test_toggle_via_api(self, api, page_goto):
        api.post("/banks/accounts", data={
            "bank_name": "Toggle Bank",
            "account_name": "Toggle Account",
            "account_number": "88889999",
            "ifsc_code": "TOGL0000001",
            "branch_name": "",
            "notes": "",
        })
        import re
        html = page_goto("/banks/manage").content()
        m = re.search(r'accounts/(\d+)/toggle', html)
        if m:
            aid = m.group(1)
            toggle_resp = api.patch(f"/banks/accounts/{aid}/toggle")
            assert toggle_resp.status_code == 200
            page2 = page_goto("/banks/manage")
            assert "Toggle Account" in page2.content()


class TestBankAccountDelete:
    def test_delete_via_api(self, api, page_goto):
        api.post("/banks/accounts", data={
            "bank_name": "Delete Bank",
            "account_name": "Delete Account",
            "account_number": "11110000",
            "ifsc_code": "DELT0000001",
            "branch_name": "",
            "notes": "",
        })
        import re
        html = page_goto("/banks/manage").content()
        m = re.search(r'hx-delete="/banks/accounts/(\d+)"', html)
        if m:
            aid = m.group(1)
            del_resp = api.delete(f"/banks/accounts/{aid}")
            assert del_resp.status_code in (200, 204)
            page2 = page_goto("/banks/manage")
            assert "Delete Account" not in page2.content()

    def test_delete_via_ui_confirm(self, page_goto, api):
        api.post("/banks/accounts", data={
            "bank_name": "UI Delete Bank",
            "account_name": "UI Delete Account",
            "account_number": "33334444",
            "ifsc_code": "UIDL0000001",
            "branch_name": "",
            "notes": "",
        })
        page = page_goto("/banks/manage")
        page.once("dialog", lambda d: d.accept())
        page.locator('button[hx-delete]').first.click()
        page.wait_for_load_state("networkidle")
        assert "UI Delete Account" not in page.content()

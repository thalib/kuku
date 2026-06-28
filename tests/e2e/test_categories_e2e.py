import re


class TestCategoriesPage:
    def test_page_loads(self, page_goto):
        page = page_goto("/banks/categories")
        assert "Transaction Categories" in page.locator("h1").text_content()

    def test_add_button_present(self, page_goto):
        page = page_goto("/banks/categories")
        assert page.get_by_text("Add Category").is_visible()

    def test_system_categories_loaded(self, page_goto):
        page = page_goto("/banks/categories")
        content = page.content()
        assert "INCOME:Sales Revenue" in content
        assert "EXPENSE:Salaries" in content

    def test_system_categories_have_lock_badge(self, page_goto):
        page = page_goto("/banks/categories")
        assert page.locator(".bi-lock-fill").count() > 0

    def test_all_five_types_present(self, page_goto):
        page = page_goto("/banks/categories")
        content = page.content()
        assert "Income" in content
        assert "Expense" in content
        assert "Asset" in content
        assert "Liability" in content
        assert "Equity" in content


class TestCategoryCreate:
    def test_add_form_opens(self, page_goto):
        page = page_goto("/banks/categories")
        page.get_by_text("Add Category").click()
        page.wait_for_load_state("networkidle")
        form = page.locator("#category-form-card form")
        assert form.is_visible()
        assert "Category Name" in page.content()

    def test_create_category_via_api(self, api, page_goto):
        resp = api.post("/banks/categories", data={
            "name": "E2E Test Category",
            "type": "Expense",
            "description": "Created during E2E test",
        })
        assert resp.status_code == 200
        page = page_goto("/banks/categories")
        assert "E2E Test Category" in page.content()

    def test_create_category_via_form(self, page_goto):
        page = page_goto("/banks/categories")
        page.get_by_text("Add Category").click()
        page.wait_for_load_state("networkidle")
        form = page.locator("#category-form-card form")
        form.locator('[name="name"]').fill("Form Created Category")
        form.locator('[name="type"]').select_option("Income")
        form.locator('[name="description"]').fill("Created via form")
        form.get_by_text("Save").click()
        page.wait_for_load_state("networkidle")
        assert "Form Created Category" in page.content()

    def test_create_income_category(self, api, page_goto):
        api.post("/banks/categories", data={
            "name": "E2E Income Cat",
            "type": "Income",
            "description": "Income test",
        })
        page = page_goto("/banks/categories")
        assert "INCOME:E2E Income Cat" in page.content()

    def test_create_asset_category(self, api, page_goto):
        api.post("/banks/categories", data={
            "name": "E2E Asset Cat",
            "type": "Asset",
            "description": "Asset test",
        })
        page = page_goto("/banks/categories")
        assert "ASSET:E2E Asset Cat" in page.content()


class TestCategoryEdit:
    def test_edit_form_opens(self, api, page_goto):
        api.post("/banks/categories", data={
            "name": "E2E Edit Target",
            "type": "Expense",
            "description": "",
        })
        page = page_goto("/banks/categories")
        page.locator('button[hx-get*="/edit"]').first.click()
        page.wait_for_load_state("networkidle")
        form = page.locator("#category-form-card form")
        assert form.is_visible()
        assert "Edit Category" in page.content()

    def test_update_category_via_api(self, api, page_goto):
        api.post("/banks/categories", data={
            "name": "E2E Update Target",
            "type": "Expense",
            "description": "",
        })
        html = page_goto("/banks/categories").content()
        m = re.search(r'categories/(\d+)/edit', html)
        if m:
            cid = m.group(1)
            resp = api.post(f"/banks/categories/{cid}/update", data={
                "name": "E2E Updated Name",
                "type": "Expense",
                "description": "Updated",
            })
            assert resp.status_code == 200
            page = page_goto("/banks/categories")
            assert "E2E Updated Name" in page.content()


class TestCategoryCancelReopen:
    def test_cancel_then_add_reopens_form(self, page_goto):
        page = page_goto("/banks/categories")
        page.evaluate('''() => {
            window._targetErrors = [];
            document.addEventListener("htmx:targetError", function(e) {
                window._targetErrors.push(e.detail ? e.detail.target : "");
            });
        }''')
        page.get_by_text("Add Category").click()
        page.wait_for_load_state("networkidle")
        assert page.locator("#category-form-card form").is_visible()
        page.get_by_text("Cancel").click()
        page.wait_for_load_state("networkidle")
        page.get_by_text("Add Category").click()
        page.wait_for_load_state("networkidle")
        assert page.locator("#category-form-card form").is_visible()
        assert page.evaluate("window._targetErrors") == []

    def test_close_button_then_add_reopens_form(self, page_goto):
        page = page_goto("/banks/categories")
        page.evaluate('''() => {
            window._targetErrors = [];
            document.addEventListener("htmx:targetError", function(e) {
                window._targetErrors.push(e.detail ? e.detail.target : "");
            });
        }''')
        page.get_by_text("Add Category").click()
        page.wait_for_load_state("networkidle")
        assert page.locator("#category-form-card form").is_visible()
        page.locator("#category-form-card .btn-close").click()
        page.wait_for_load_state("networkidle")
        page.get_by_text("Add Category").click()
        page.wait_for_load_state("networkidle")
        assert page.locator("#category-form-card form").is_visible()
        assert page.evaluate("window._targetErrors") == []


class TestCategoryDelete:
    def test_delete_user_category_via_api(self, api, page_goto):
        api.post("/banks/categories", data={
            "name": "E2E Delete Target",
            "type": "Expense",
            "description": "",
        })
        html = page_goto("/banks/categories").content()
        m = re.search(r'data-url="/banks/categories/(\d+)"', html)
        if m:
            cid = m.group(1)
            resp = api.delete(f"/banks/categories/{cid}")
            assert resp.status_code == 200
            page = page_goto("/banks/categories")
            assert "E2E Delete Target" not in page.content()

    def test_delete_via_ui_confirm(self, api, page_goto):
        api.post("/banks/categories", data={
            "name": "E2E UI Delete Target",
            "type": "Expense",
            "description": "",
        })
        page = page_goto("/banks/categories")
        row = page.locator("tr", has_text="E2E UI Delete Target")
        delete_btn = row.locator('.kuku-del-btn')
        delete_btn.click()
        page.wait_for_selector('#kukuDeleteModal.show')
        page.fill('#kd-input', 'DELETE')
        page.click('#kd-btn')
        page.wait_for_load_state("networkidle")
        assert "E2E UI Delete Target" not in page.content()

    def test_system_category_no_edit_delete_buttons(self, page_goto):
        page = page_goto("/banks/categories")
        system_badge = page.locator("text=System").first
        parent_row = system_badge.locator("xpath=ancestor::tr")
        assert parent_row.locator('.kuku-del-btn').count() == 0
        assert parent_row.locator('button[hx-get*="edit"]').count() == 0

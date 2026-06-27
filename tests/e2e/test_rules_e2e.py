import re


def _get_latest_cat_id(api):
    cats_html = api.get("/banks/categories").text
    cat_ids = re.findall(r'categories/(\d+)/edit', cats_html)
    return cat_ids[-1] if cat_ids else "1"


class TestRulesPage:
    def test_page_loads(self, page_goto):
        page = page_goto("/banks/rules")
        assert "Classification Rules" in page.locator("h1").text_content()

    def test_add_button_present(self, page_goto):
        page = page_goto("/banks/rules")
        assert page.get_by_text("Add Rule").is_visible()

    def test_empty_state_shown(self, page_goto):
        page = page_goto("/banks/rules")
        assert "No rules yet" in page.content()


class TestRuleCreate:
    def test_add_form_opens(self, page_goto):
        page = page_goto("/banks/rules")
        page.get_by_text("Add Rule").click()
        page.wait_for_load_state("networkidle")
        form = page.locator("#rule-form-card form")
        assert form.is_visible()
        assert "Search Text" in page.content()
        assert "Match Type" in page.content()
        assert "Category" in page.content()

    def test_create_rule_via_api(self, api, page_goto):
        api.post("/banks/categories", data={
            "name": "E2E Rule Target Cat",
            "type": "Expense",
            "description": "",
        })
        cat_id = _get_latest_cat_id(api)
        resp = api.post("/banks/rules", data={
            "search_text": "NEFT_E2E",
            "match_type": "contains",
            "category_id": cat_id,
            "priority": "1",
            "applies_to": "both",
            "is_active": "on",
        })
        assert resp.status_code == 200
        page = page_goto("/banks/rules")
        assert "NEFT_E2E" in page.content()

    def test_create_rule_via_form(self, api, page_goto):
        api.post("/banks/categories", data={
            "name": "E2E Form Rule Target Cat",
            "type": "Expense",
            "description": "",
        })
        cat_id = _get_latest_cat_id(api)
        resp = api.post("/banks/rules", data={
            "search_text": "SALARY_TEST",
            "match_type": "contains",
            "category_id": cat_id,
            "priority": "5",
            "applies_to": "both",
            "is_active": "on",
        })
        assert resp.status_code == 200
        page = page_goto("/banks/rules")
        assert "SALARY_TEST" in page.content()


class TestRuleEdit:
    def test_edit_form_opens(self, api, page_goto):
        api.post("/banks/categories", data={
            "name": "E2E Edit Rule Target Cat",
            "type": "Expense",
            "description": "",
        })
        cat_id = _get_latest_cat_id(api)
        api.post("/banks/rules", data={
            "search_text": "EDITTEST",
            "match_type": "contains",
            "category_id": cat_id,
            "priority": "0",
            "applies_to": "both",
            "is_active": "on",
        })
        page = page_goto("/banks/rules")
        page.locator('button[hx-get*="rules/"][hx-get*="/edit"]').first.click()
        page.wait_for_load_state("networkidle")
        form = page.locator("#rule-form-card form")
        assert form.is_visible()
        assert "Edit Rule" in page.content()


class TestRuleToggle:
    def test_toggle_rule_via_api(self, api, page_goto):
        api.post("/banks/categories", data={
            "name": "E2E Toggle Rule Target Cat",
            "type": "Expense",
            "description": "",
        })
        cat_id = _get_latest_cat_id(api)
        api.post("/banks/rules", data={
            "search_text": "TOGGLETEST",
            "match_type": "contains",
            "category_id": cat_id,
            "priority": "0",
            "applies_to": "both",
            "is_active": "on",
        })
        page = page_goto("/banks/rules")
        html = page.content()
        m = re.search(r'rules/(\d+)/toggle', html)
        assert m is not None
        rid = m.group(1)
        toggle_resp = api.patch(f"/banks/rules/{rid}/toggle")
        assert toggle_resp.status_code == 200
        page2 = page_goto("/banks/rules")
        assert "TOGGLETEST" in page2.content()


class TestRuleCancelReopen:
    def test_cancel_then_add_reopens_form(self, page_goto):
        page = page_goto("/banks/rules")
        page.evaluate('''() => {
            window._targetErrors = [];
            document.addEventListener("htmx:targetError", function(e) {
                window._targetErrors.push(e.detail ? e.detail.target : "");
            });
        }''')
        page.get_by_text("Add Rule").click()
        page.wait_for_load_state("networkidle")
        assert page.locator("#rule-form-card form").is_visible()
        page.get_by_text("Cancel").click()
        page.wait_for_load_state("networkidle")
        page.get_by_text("Add Rule").click()
        page.wait_for_load_state("networkidle")
        assert page.locator("#rule-form-card form").is_visible()
        assert page.evaluate("window._targetErrors") == []


class TestRuleDelete:
    def test_delete_rule_via_api(self, api, page_goto):
        api.post("/banks/categories", data={
            "name": "E2E Delete Rule Target Cat",
            "type": "Expense",
            "description": "",
        })
        cat_id = _get_latest_cat_id(api)
        resp = api.post("/banks/rules", data={
            "search_text": "DELETETEST",
            "match_type": "contains",
            "category_id": cat_id,
            "priority": "0",
            "applies_to": "both",
            "is_active": "on",
        })
        m = re.search(r'DELETETEST.*?hx-delete="/banks/rules/(\d+)"', resp.text, re.DOTALL)
        if not m:
            m = re.search(r'hx-delete="/banks/rules/(\d+)".*?DELETETEST', resp.text, re.DOTALL)
        assert m is not None, "DELETE rule not found in response"
        rid = m.group(1)
        del_resp = api.delete(f"/banks/rules/{rid}")
        assert del_resp.status_code == 200
        page2 = page_goto("/banks/rules")
        assert "DELETETEST" not in page2.content()

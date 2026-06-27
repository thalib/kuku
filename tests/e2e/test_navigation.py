class TestNavigation:
    def test_dashboard_loads(self, page_goto):
        page = page_goto("/")
        assert "Kuku" in page.title()

    def test_sidebar_visible(self, page_goto):
        page = page_goto("/")
        sidebar = page.locator("#sidebarWrap")
        assert sidebar.is_visible()

    def test_sidebar_toggle_closes_sidebar(self, page_goto):
        page = page_goto("/")
        page.locator("#sidebarToggle").click()
        page.wait_for_timeout(300)
        assert page.locator("#sidebarWrap").evaluate("el => el.classList.contains('closed')")

    def test_sidebar_toggle_reopens_sidebar(self, page_goto):
        page = page_goto("/")
        page.locator("#sidebarToggle").click()
        page.wait_for_timeout(300)
        page.locator("#sidebarToggle").click()
        page.wait_for_timeout(300)
        assert not page.locator("#sidebarWrap").evaluate("el => el.classList.contains('closed')")

    def test_sidebar_dashboard_active(self, page_goto):
        page = page_goto("/")
        dashboard_link = page.locator('.app-sidebar-wrap a[href="/"]')
        assert "bg-primary" in dashboard_link.get_attribute("class")

    def test_sidebar_manage_active_on_banks_manage(self, page_goto):
        page = page_goto("/banks/manage")
        manage_link = page.locator('a[href="/banks/manage"]')
        assert "bg-primary" in manage_link.get_attribute("class")

    def test_sidebar_transactions_active_on_transactions(self, page_goto):
        page = page_goto("/banks/transactions")
        tx_link = page.locator('a[href="/banks/transactions"]')
        assert "bg-primary" in tx_link.get_attribute("class")

    def test_sidebar_categories_active_on_categories(self, page_goto):
        page = page_goto("/banks/categories")
        cat_link = page.locator('a[href="/banks/categories"]')
        assert "bg-primary" in cat_link.get_attribute("class")

    def test_sidebar_rules_active_on_rules(self, page_goto):
        page = page_goto("/banks/rules")
        rule_link = page.locator('a[href="/banks/rules"]')
        assert "bg-primary" in rule_link.get_attribute("class")

    def test_navigate_to_bank_accounts_via_sidebar(self, page_goto):
        page = page_goto("/")
        page.locator('a[href="/banks/manage"]').click()
        page.wait_for_load_state("networkidle")
        assert "/banks/manage" in page.url
        assert page.locator("h1").text_content() == "Bank Accounts"

    def test_navigate_to_transactions_via_sidebar(self, page_goto):
        page = page_goto("/")
        page.locator('a[href="/banks/transactions"]').click()
        page.wait_for_load_state("networkidle")
        assert "/banks/transactions" in page.url
        assert "Transactions" in page.locator("h1").text_content()

    def test_navigate_to_categories_via_sidebar(self, page_goto):
        page = page_goto("/")
        page.locator('a[href="/banks/categories"]').click()
        page.wait_for_load_state("networkidle")
        assert "/banks/categories" in page.url
        assert "Categories" in page.locator("h1").text_content()

    def test_navigate_to_rules_via_sidebar(self, page_goto):
        page = page_goto("/")
        page.locator('a[href="/banks/rules"]').click()
        page.wait_for_load_state("networkidle")
        assert "/banks/rules" in page.url
        assert "Classification Rules" in page.locator("h1").text_content()

    def test_navigate_to_reports(self, page_goto):
        page = page_goto("/")
        page.locator('a[href="/reports"]').click()
        page.wait_for_load_state("networkidle")
        assert "/reports" in page.url
        assert "Reports" in page.locator("h1").text_content()

    def test_navigate_to_settings(self, page_goto):
        page = page_goto("/")
        page.locator('a[href="/settings"]').click()
        page.wait_for_load_state("networkidle")
        assert "/settings" in page.url
        assert "Settings" in page.locator("h1").text_content()

    def test_sidebar_group_labels_present(self, page_goto):
        page = page_goto("/")
        content = page.content()
        assert "BANKS" in content
        assert "REPORTS" in content
        assert "ADMIN" in content

    def test_sidebar_shows_app_name(self, page_goto):
        page = page_goto("/")
        assert page.locator(".app-sidebar").get_by_text("Kuku").is_visible()

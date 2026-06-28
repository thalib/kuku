class TestDashboard:
    def test_page_title(self, page_goto):
        page = page_goto("/")
        assert "Dashboard" in page.title()

    def test_no_coming_soon_message(self, page_goto):
        page = page_goto("/")
        assert "Coming soon" not in page.content()

    def test_recent_estimates_section(self, page_goto):
        page = page_goto("/")
        assert "Recent Estimates" in page.content()

    def test_sidebar_present(self, page_goto):
        page = page_goto("/")
        assert page.locator("#sidebarWrap").is_visible()

    def test_coming_soon_pages_show_message(self, page_goto):
        for path, label in [("/reports", "Reports")]:
            page = page_goto(path)
            assert "Coming soon" in page.content()
            assert label in page.content()

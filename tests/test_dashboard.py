import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


class TestDashboard:

    def test_get_root_returns_200(self, client):
        assert client.get("/").status_code == 200

    def test_page_title_contains_kuku(self, client):
        assert "Kuku" in client.get("/").text

    def test_sidebar_groups_present(self, client):
        body = client.get("/").text
        for group in ["BANKS", "REPORTS", "ADMIN"]:
            assert group in body, f"Sidebar missing group: {group}"

    def test_dashboard_active_nav_highlighted(self, client):
        body = client.get("/").text
        assert "bg-primary" in body
        assert "bi-speedometer2" in body

    def test_dashboard_recent_estimates_table(self, client):
        assert "Recent Estimates" in client.get("/").text


PAGE_CASES = [
    ("/banks/manage", "Banks - Manage", "Banks - Manage"),
    ("/banks/transactions", "Banks - Transaction", "Banks - Transaction"),
    ("/reports", "Reports", "Reports"),
    ("/settings", "Admin - Settings", "Admin - Settings"),
]


class TestComingSoonPages:

    @pytest.mark.parametrize("url, page_name, expected_title", PAGE_CASES)
    def test_page_returns_200(self, client, url, page_name, expected_title):
        assert client.get(url).status_code == 200

    @pytest.mark.parametrize("url, page_name, expected_title", PAGE_CASES)
    def test_page_shows_coming_soon(self, client, url, page_name, expected_title):
        body = client.get(url).text
        assert "Coming soon" in body
        assert page_name in body

    @pytest.mark.parametrize("url, page_name, expected_title", PAGE_CASES)
    def test_sidebar_present(self, client, url, page_name, expected_title):
        body = client.get(url).text
        assert 'id="kukuSidebarShell"' in body
        assert "BANKS" in body

    @pytest.mark.parametrize("url, page_name, expected_title", PAGE_CASES)
    def test_correct_nav_item_active(self, client, url, page_name, expected_title):
        body = client.get(url).text
        assert "bg-primary" in body

    def test_dashboard_coming_soon_not_shown(self, client):
        body = client.get("/").text
        assert "Coming soon" not in body

    def test_bank_manage_active_nav(self, client):
        body = client.get("/banks/manage").text
        assert 'href="/banks/manage"' in body

    def test_banks_transactions_active_nav(self, client):
        body = client.get("/banks/transactions").text
        assert 'href="/banks/transactions"' in body

    def test_reports_active_nav(self, client):
        body = client.get("/reports").text
        assert 'href="/reports"' in body

    def test_settings_active_nav(self, client):
        body = client.get("/settings").text
        assert 'href="/settings"' in body

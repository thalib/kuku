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

    def test_sidebar_toggle_button(self, client):
        body = client.get("/").text
        assert "sidebarToggle" in body
        assert "bi-layout-sidebar-inset-reverse" in body

    def test_sidebar_wrap_id(self, client):
        body = client.get("/").text
        assert 'id="sidebarWrap"' in body


PAGE_CASES = [
    ("/banks/manage", "Banks - Manage"),
    ("/banks/transactions", "Banks - Transaction"),
    ("/reports", "Reports"),
    ("/settings", "Admin - Settings"),
]


class TestComingSoonPages:

    @pytest.mark.parametrize("url,page_name", PAGE_CASES)
    def test_page_returns_200(self, client, url, page_name):
        assert client.get(url).status_code == 200

    @pytest.mark.parametrize("url,page_name", PAGE_CASES)
    def test_page_shows_coming_soon(self, client, url, page_name):
        body = client.get(url).text
        assert "Coming soon" in body
        assert page_name in body

    @pytest.mark.parametrize("url,page_name", PAGE_CASES)
    def test_sidebar_present(self, client, url, page_name):
        body = client.get(url).text
        assert 'id="sidebarWrap"' in body

    @pytest.mark.parametrize("url,page_name", PAGE_CASES)
    def test_correct_nav_item_active(self, client, url, page_name):
        body = client.get(url).text
        assert "bg-primary" in body

    def test_dashboard_coming_soon_not_shown(self, client):
        assert "Coming soon" not in client.get("/").text

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


class TestDashboard:

    def test_get_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_page_title_contains_kuku(self, client):
        response = client.get("/")
        assert "Kuku" in response.text

    def test_offcanvas_sidebar_present(self, client):
        response = client.get("/")
        assert 'id="offcanvasSidebar"' in response.text
        assert "offcanvas offcanvas-start" in response.text

    def test_sidebar_contains_all_nav_items(self, client):
        response = client.get("/")
        expected_links = ["Dashboard", "Transactions", "GST", "Reports"]
        for item in expected_links:
            assert item in response.text, f"Sidebar missing: {item}"

    def test_active_dashboard_nav_item(self, client):
        response = client.get("/")
        assert "bg-primary" in response.text
        assert "bi-speedometer2" in response.text

    def test_navbar_hamburger_toggle(self, client):
        response = client.get("/")
        assert "bi-list" in response.text
        assert "data-bs-toggle=" in response.text
        assert "offcanvasSidebar" in response.text

    def test_navbar_brand(self, client):
        response = client.get("/")
        assert "navbar-brand" in response.text
        assert "Kuku" in response.text

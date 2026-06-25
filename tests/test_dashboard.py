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

    def test_sidebar_present_with_correct_id(self, client):
        assert 'id="kukuSidebarShell"' in client.get("/").text
        assert "app-sidebar" in client.get("/").text

    def test_sidebar_groups_present(self, client):
        body = client.get("/").text
        for group in ["Workspace", "Items", "Sales", "Purchase", "Admin"]:
            assert group in body, f"Sidebar missing group: {group}"

    def test_dashboard_active_nav_highlighted(self, client):
        assert "bg-primary" in client.get("/").text
        assert "bi-speedometer2" in client.get("/").text

    def test_navbar_hamburger_toggle_button(self, client):
        body = client.get("/").text
        assert "kukuToggleBtn" in body
        assert "bi-layout-sidebar-inset-reverse" in body

    def test_navbar_brand(self, client):
        body = client.get("/").text
        assert "navbar-brand" in body
        assert "sticky-top" in body

    def test_navbar_user_dropdown(self, client):
        body = client.get("/").text
        assert "dropdown" in body
        assert "person-circle" in body

    def test_sidebar_footer(self, client):
        body = client.get("/").text
        assert "border-top" in body
        assert "bi-moon-stars-fill" in body

    def test_dashboard_server_health_card(self, client):
        body = client.get("/").text
        assert "Server Health" in body
        assert "data-testid=" in body

    def test_dashboard_quick_links(self, client):
        body = client.get("/").text
        assert "Quick Links" in body
        assert "btn-success" in body

    def test_dashboard_recent_estimates_table(self, client):
        body = client.get("/").text
        assert "Recent Estimates" in body
        assert "EST260701" in body

    def test_dashboard_recent_invoices_table(self, client):
        body = client.get("/").text
        assert "Recent Invoices" in body
        assert "INM260466" in body

    def test_update_button_present(self, client):
        body = client.get("/").text
        assert "dashboard-update" in body
        assert "Update" in body

import pytest
from fastapi.testclient import TestClient
from app import config, database


@pytest.fixture(autouse=True)
async def _fresh_db():
    config.DB_PATH = ":memory:"
    database._db = None
    await database.init_db()
    yield
    await database.close_db()


@pytest.fixture()
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture()
async def _seed_user_category():
    from app.services.categories import create_category
    from app.database import get_db
    from app.models.categories import CategoryCreate
    db = await get_db()
    return await create_category(
        db,
        CategoryCreate(
            name="Custom Test Category",
            type="Expense",
            description="A user-created category for testing",
        ),
    )


@pytest.fixture()
async def _seed_system_category():
    from app.services.categories import list_categories
    from app.database import get_db
    db = await get_db()
    cats = await list_categories(db)
    system_cats = [c for c in cats if c["is_system"]]
    return system_cats[0] if system_cats else None


class TestCategoriesSeeding:
    def test_system_categories_seeded_on_init(self, client):
        resp = client.get("/banks/categories")
        body = resp.text
        assert "INCOME:Sales Revenue" in body
        assert "EXPENSE:Salaries &amp; Wages" in body
        assert "ASSET:Cash &amp; Bank" in body
        assert "LIABILITY:Accounts Payable" in body
        assert "EQUITY:Owner Capital" in body

    def test_system_categories_seeded_once(self, client):
        from app.services.categories import list_categories
        import asyncio

        async def _count():
            db = await database.get_db()
            cats = await list_categories(db)
            return len([c for c in cats if c["is_system"]])

        count = asyncio.get_event_loop().run_until_complete(_count())
        assert count > 0

    def test_all_five_types_present(self, client):
        resp = client.get("/banks/categories")
        body = resp.text
        assert ">Income<" in body
        assert ">Expense<" in body
        assert ">Asset<" in body
        assert ">Liability<" in body
        assert ">Equity<" in body


class TestCategoriesPage:
    def test_get_returns_200(self, client):
        assert client.get("/banks/categories").status_code == 200

    def test_page_has_heading(self, client):
        assert "Transaction Categories" in client.get("/banks/categories").text

    def test_page_has_add_button(self, client):
        assert "Add Category" in client.get("/banks/categories").text


class TestCategoriesAdd:
    def test_form_endpoint_returns_form(self, client):
        resp = client.get("/banks/categories/form")
        assert resp.status_code == 200
        assert "name" in resp.text
        assert "type" in resp.text

    def test_create_category_appends_to_list(self, client):
        payload = {
            "name": "Custom Income Stream",
            "type": "Income",
            "description": "Custom income category",
        }
        resp = client.post("/banks/categories", data=payload)
        assert resp.status_code == 200
        body = resp.text
        assert "Custom Income Stream" in body

    def test_create_without_description(self, client):
        payload = {
            "name": "No Desc Category",
            "type": "Expense",
            "description": "",
        }
        resp = client.post("/banks/categories", data=payload)
        assert resp.status_code == 200
        assert "No Desc Category" in resp.text


class TestCategoriesEdit:
    def test_edit_form_endpoint_returns_form(self, client, _seed_user_category):
        cat = _seed_user_category
        resp = client.get(f"/banks/categories/{cat['id']}/edit")
        assert resp.status_code == 200
        assert f'value="{cat["name"]}"' in resp.text
        assert "Edit Category" in resp.text

    def test_update_category_changes_name(self, client, _seed_user_category):
        cat = _seed_user_category
        payload = {
            "name": "Updated Category Name",
            "type": "Expense",
            "description": "Updated description",
        }
        resp = client.post(f"/banks/categories/{cat['id']}/update", data=payload)
        assert resp.status_code == 200
        assert "Updated Category Name" in resp.text

    def test_cannot_edit_system_category(self, client, _seed_system_category):
        cat = _seed_system_category
        payload = {
            "name": "Hacked Name",
            "type": "Expense",
            "description": "",
        }
        resp = client.post(f"/banks/categories/{cat['id']}/update", data=payload)
        assert resp.status_code == 404


class TestCategoriesDelete:
    def test_delete_user_category(self, client, _seed_user_category):
        cat = _seed_user_category
        resp = client.delete(f"/banks/categories/{cat['id']}")
        assert resp.status_code == 200
        body = client.get("/banks/categories").text
        assert "Custom Test Category" not in body

    def test_cannot_delete_system_category(self, client, _seed_system_category):
        cat = _seed_system_category
        resp = client.delete(f"/banks/categories/{cat['id']}")
        assert resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/banks/categories/99999")
        assert resp.status_code == 404


class TestCategoriesList:
    def test_system_categories_shown_with_lock_badge(self, client, _seed_system_category):
        body = client.get("/banks/categories").text
        assert "bi-lock-fill" in body
        assert "System" in body

    def test_user_categories_show_edit_delete_actions(self, client, _seed_user_category):
        body = client.get("/banks/categories").text
        assert "bi-pencil" in body
        assert "bi-trash" in body

    def test_clear_form_endpoint(self, client):
        resp = client.get("/banks/categories/clear-form")
        assert resp.status_code == 200

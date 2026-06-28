import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from app import config, database


@pytest_asyncio.fixture(autouse=True)
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


@pytest_asyncio.fixture()
async def _seed_category():
    from app.services.categories import create_category
    from app.database import get_db
    from app.models.categories import CategoryCreate
    db = await get_db()
    return await create_category(
        db,
        CategoryCreate(
            name="Test Rule Category",
            type="Expense",
            description="For rule testing",
        ),
    )


@pytest_asyncio.fixture()
async def _seed_rule(_seed_category):
    from app.services.rules import create_rule
    from app.database import get_db
    from app.models.rules import RuleCreate
    db = await get_db()
    return await create_rule(
        db,
        RuleCreate(
            search_text="NEFT",
            match_type="contains",
            category_id=_seed_category["id"],
            priority=1,
            applies_to="both",
            is_active=True,
        ),
    )


class TestRulesPage:
    def test_get_returns_200(self, client):
        assert client.get("/banks/rules").status_code == 200

    def test_page_has_heading(self, client):
        assert "Classification Rules" in client.get("/banks/rules").text

    def test_page_has_add_button(self, client):
        assert "Add Rule" in client.get("/banks/rules").text

    def test_empty_state_when_no_rules(self, client):
        body = client.get("/banks/rules").text
        assert "No rules yet" in body


class TestRulesAdd:
    def test_form_endpoint_returns_form(self, client, _seed_category):
        resp = client.get("/banks/rules/form")
        assert resp.status_code == 200
        assert "search_text" in resp.text
        assert "match_type" in resp.text
        assert "category_id" in resp.text

    def test_create_rule_appends_to_list(self, client, _seed_category):
        payload = {
            "search_text": "Salary",
            "match_type": "contains",
            "category_id": str(_seed_category["id"]),
            "priority": "0",
            "applies_to": "both",
            "is_active": "on",
        }
        resp = client.post("/banks/rules", data=payload)
        assert resp.status_code == 200
        body = resp.text
        assert "Salary" in body

    def test_create_rule_without_priority(self, client, _seed_category):
        payload = {
            "search_text": "POS",
            "match_type": "equals",
            "category_id": str(_seed_category["id"]),
            "priority": "",
            "applies_to": "debit",
            "is_active": "on",
        }
        resp = client.post("/banks/rules", data=payload)
        assert resp.status_code == 200
        assert "POS" in resp.text

    def test_create_rule_invalid_returns_form(self, client, _seed_category):
        payload = {
            "search_text": "A",
            "match_type": "contains",
            "category_id": "not_a_number",
            "priority": "0",
            "applies_to": "both",
            "is_active": "on",
        }
        resp = client.post("/banks/rules", data=payload)
        assert resp.status_code == 200
        assert "Invalid input" in resp.text


class TestRulesEdit:
    def test_edit_form_endpoint_returns_form(self, client, _seed_rule):
        rule = _seed_rule
        resp = client.get(f"/banks/rules/{rule['id']}/edit")
        assert resp.status_code == 200
        assert f'value="{rule["search_text"]}"' in resp.text
        assert "Edit Rule" in resp.text

    def test_update_rule_changes_text(self, client, _seed_rule):
        rule = _seed_rule
        payload = {
            "search_text": "Updated Text",
            "match_type": "equals",
            "category_id": str(rule["category_id"]),
            "priority": "5",
            "applies_to": "credit",
            "is_active": "on",
        }
        resp = client.post(f"/banks/rules/{rule['id']}/update", data=payload)
        assert resp.status_code == 200
        assert "Updated Text" in resp.text

    def test_update_nonexistent_returns_404(self, client):
        payload = {
            "search_text": "Test",
            "match_type": "contains",
            "category_id": "1",
            "priority": "0",
            "applies_to": "both",
            "is_active": "on",
        }
        resp = client.post("/banks/rules/99999/update", data=payload)
        assert resp.status_code == 404


class TestRulesDelete:
    def test_delete_rule(self, client, _seed_rule):
        rule = _seed_rule
        resp = client.delete(f"/banks/rules/{rule['id']}")
        assert resp.status_code == 200
        body = client.get("/banks/rules").text
        assert rule["search_text"] not in body

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/banks/rules/99999")
        assert resp.status_code == 404


class TestRulesToggle:
    def test_toggle_active_to_inactive(self, client, _seed_rule):
        rule = _seed_rule
        resp = client.patch(f"/banks/rules/{rule['id']}/toggle")
        assert resp.status_code == 200
        body = client.get("/banks/rules").text
        assert rule["search_text"] in body

    def test_toggle_inactive_to_active(self, client, _seed_rule):
        rule = _seed_rule
        client.patch(f"/banks/rules/{rule['id']}/toggle")
        resp = client.patch(f"/banks/rules/{rule['id']}/toggle")
        assert resp.status_code == 200

    def test_toggle_nonexistent_returns_404(self, client):
        resp = client.patch("/banks/rules/99999/toggle")
        assert resp.status_code == 404


class TestRulesPriority:
    def test_priority_is_plain_text_not_input(self, client, _seed_rule):
        body = client.get("/banks/rules").text
        assert 'type="number"' not in body
        assert "fw-semibold" in body

    def test_update_priority_via_form(self, client, _seed_rule):
        rule = _seed_rule
        payload = {
            "search_text": rule["search_text"],
            "match_type": rule["match_type"],
            "category_id": str(rule["category_id"]),
            "priority": "99",
            "applies_to": rule.get("applies_to", "both"),
            "is_active": "on",
        }
        resp = client.post(f"/banks/rules/{rule['id']}/update", data=payload)
        assert resp.status_code == 200
        body = client.get("/banks/rules").text
        assert "99" in body


class TestRulesList:
    def test_clear_form_endpoint(self, client):
        resp = client.get("/banks/rules/clear-form")
        assert resp.status_code == 200

    async def test_rules_sorted_by_priority(self, client, _seed_category):
        from app.services.rules import create_rule
        from app.database import get_db
        from app.models.rules import RuleCreate

        db = await get_db()
        await create_rule(db, RuleCreate(search_text="AAA", match_type="contains", category_id=_seed_category["id"], priority=5))
        await create_rule(db, RuleCreate(search_text="BBB", match_type="contains", category_id=_seed_category["id"], priority=1))
        body = client.get("/banks/rules").text
        bbb_pos = body.find("BBB")
        aaa_pos = body.find("AAA")
        assert bbb_pos < aaa_pos

    async def test_inactive_rule_still_shown(self, client, _seed_rule):
        from app.services.rules import toggle_rule
        from app.database import get_db

        db = await get_db()
        await toggle_rule(db, _seed_rule["id"])
        body = client.get("/banks/rules").text
        assert _seed_rule["search_text"] in body

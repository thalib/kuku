import aiosqlite
from datetime import datetime, timezone
from app.models.rules import RuleCreate, RuleUpdate


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    return dict(row)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_rule(db: aiosqlite.Connection, data: RuleCreate) -> dict:
    now = _now()
    cursor = await db.execute(
        """INSERT INTO classification_rules
           (search_text, match_type, category_id, priority, applies_to, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (data.search_text, data.match_type, data.category_id, data.priority, data.applies_to, 1 if data.is_active else 0, now, now),
    )
    await db.commit()
    return await get_rule(db, cursor.lastrowid)


async def get_rule(db: aiosqlite.Connection, rule_id: int) -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM classification_rules WHERE id = ?", (rule_id,)
    )
    return _row_to_dict(await cursor.fetchone())


async def list_rules(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM classification_rules ORDER BY priority ASC, id ASC"
    )
    return [_row_to_dict(r) for r in await cursor.fetchall()]


async def update_rule(db: aiosqlite.Connection, rule_id: int, data: RuleUpdate) -> dict | None:
    sets, vals = [], []
    for key in ("search_text", "match_type", "category_id", "priority", "applies_to", "is_active"):
        val = getattr(data, key)
        if val is not None:
            sets.append(f"{key} = ?")
            if key == "is_active":
                vals.append(1 if val else 0)
            else:
                vals.append(val)
    if not sets:
        return await get_rule(db, rule_id)
    sets.append("updated_at = ?")
    vals.append(_now())
    vals.append(rule_id)
    cursor = await db.execute(
        f"UPDATE classification_rules SET {', '.join(sets)} WHERE id = ?",
        vals,
    )
    await db.commit()
    if cursor.rowcount == 0:
        return None
    return await get_rule(db, rule_id)


async def toggle_rule(db: aiosqlite.Connection, rule_id: int) -> dict | None:
    cursor = await db.execute(
        "SELECT is_active FROM classification_rules WHERE id = ?", (rule_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    new_state = 0 if row["is_active"] else 1
    cursor2 = await db.execute(
        "UPDATE classification_rules SET is_active = ?, updated_at = ? WHERE id = ?",
        (new_state, _now(), rule_id),
    )
    await db.commit()
    if cursor2.rowcount == 0:
        return None
    return await get_rule(db, rule_id)


async def delete_rule(db: aiosqlite.Connection, rule_id: int) -> bool:
    cursor = await db.execute(
        "DELETE FROM classification_rules WHERE id = ?", (rule_id,)
    )
    await db.commit()
    return cursor.rowcount > 0

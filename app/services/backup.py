import json
import aiosqlite
from datetime import datetime, timezone

_BACKUP_VERSION = 1


async def export_data(db: aiosqlite.Connection) -> str:
    cursor = await db.execute(
        "SELECT id, bank_name, account_name, account_number, ifsc_code, branch_name, notes, is_active, is_system"
        " FROM bank_accounts WHERE is_system = 0 ORDER BY id"
    )
    accounts = [dict(r) for r in await cursor.fetchall()]

    cursor = await db.execute(
        "SELECT id, name, type, description, is_system"
        " FROM transaction_categories ORDER BY id"
    )
    all_categories = [dict(r) for r in await cursor.fetchall()]
    categories_to_export = []
    cat_name_to_id = {}
    for c in all_categories:
        if c["is_system"] == 0:
            categories_to_export.append({
                "name": c["name"],
                "type": c["type"],
                "description": c["description"],
            })
        cat_name_to_id[c["id"]] = c

    cursor = await db.execute(
        "SELECT id, search_text, match_type, category_id, priority, applies_to, is_active"
        " FROM classification_rules ORDER BY priority, id"
    )
    rules_raw = [dict(r) for r in await cursor.fetchall()]

    cat_id_to_key = {}
    for c in all_categories:
        cat_id_to_key[c["id"]] = {"name": c["name"], "type": c["type"]}

    rules = []
    for r in rules_raw:
        cat_ref = cat_id_to_key.get(r["category_id"])
        if not cat_ref:
            continue
        rules.append({
            "search_text": r["search_text"],
            "match_type": r["match_type"],
            "category_name": cat_ref["name"],
            "category_type": cat_ref["type"],
            "priority": r["priority"],
            "applies_to": r["applies_to"],
        })

    payload = {
        "version": _BACKUP_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "bank_accounts": accounts,
        "categories": categories_to_export,
        "rules": rules,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


async def import_data(db: aiosqlite.Connection, payload: dict) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-6] + "Z"
    stats = {"accounts_created": 0, "categories_created": 0, "rules_created": 0, "skipped": {"accounts": 0, "categories": 0, "rules": 0}}

    if payload.get("version", 0) != _BACKUP_VERSION:
        raise ValueError(f"Unsupported backup version: {payload.get('version')}")

    accounts = payload.get("bank_accounts", [])
    for acc in accounts:
        cursor = await db.execute(
            "SELECT id FROM bank_accounts WHERE bank_name = ? AND account_name = ? AND account_number = ?",
            (acc["bank_name"], acc["account_name"], acc["account_number"]),
        )
        if await cursor.fetchone():
            stats["skipped"]["accounts"] += 1
            continue
        await db.execute(
            """INSERT INTO bank_accounts
               (bank_name, account_name, account_number, ifsc_code, branch_name, notes, is_active, is_system, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (acc["bank_name"], acc["account_name"], acc["account_number"],
             acc["ifsc_code"], acc.get("branch_name"), acc.get("notes"),
             acc.get("is_active", 1), now, now),
        )
        from app.services.categories import create_transfer_categories
        try:
            await create_transfer_categories(db, acc["bank_name"], acc["account_name"])
        except aiosqlite.IntegrityError:
            pass
        stats["accounts_created"] += 1

    categories = payload.get("categories", [])
    for cat in categories:
        cursor = await db.execute(
            "SELECT id FROM transaction_categories WHERE name = ? AND type = ?",
            (cat["name"], cat["type"]),
        )
        if await cursor.fetchone():
            stats["skipped"]["categories"] += 1
            continue
        await db.execute(
            """INSERT INTO transaction_categories
               (name, type, description, is_system, created_at, updated_at)
               VALUES (?, ?, ?, 0, ?, ?)""",
            (cat["name"], cat["type"], cat.get("description"), now, now),
        )
        stats["categories_created"] += 1

    await db.commit()

    cursor = await db.execute("SELECT id, name, type FROM transaction_categories")
    cat_lookup = {}
    for row in await cursor.fetchall():
        cat_lookup[(row["name"], row["type"])] = row["id"]

    rules = payload.get("rules", [])
    for rule in rules:
        cat_key = (rule["category_name"], rule["category_type"])
        cat_id = cat_lookup.get(cat_key)
        if not cat_id:
            stats["skipped"]["rules"] += 1
            continue
        cursor = await db.execute(
            "SELECT id FROM classification_rules WHERE search_text = ? AND match_type = ? AND category_id = ? AND priority = ?",
            (rule["search_text"], rule["match_type"], cat_id, rule["priority"]),
        )
        if await cursor.fetchone():
            stats["skipped"]["rules"] += 1
            continue
        await db.execute(
            """INSERT INTO classification_rules
               (search_text, match_type, category_id, priority, applies_to, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
            (rule["search_text"], rule["match_type"], cat_id, rule["priority"],
             rule.get("applies_to", "both"), now, now),
        )
        stats["rules_created"] += 1

    await db.commit()
    return stats

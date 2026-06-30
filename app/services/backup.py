import json
import aiosqlite
from datetime import datetime, timezone
from typing import Any

_BACKUP_VERSION = 2
_APP_NAME = "Kuku"
_APP_VERSION = "1.0"


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
    for c in all_categories:
        if c["is_system"] == 0:
            categories_to_export.append({
                "name": c["name"],
                "type": c["type"],
                "description": c["description"],
            })

    cursor = await db.execute(
        "SELECT id, search_text, match_type, category_id, priority, applies_to, is_active, account_id"
        " FROM classification_rules ORDER BY priority, id"
    )
    rules_raw = [dict(r) for r in await cursor.fetchall()]

    cat_id_to_key = {}
    for c in all_categories:
        cat_id_to_key[c["id"]] = {"name": c["name"], "type": c["type"]}

    acc_id_to_key = {}
    cursor = await db.execute(
        "SELECT id, bank_name, account_name, account_number FROM bank_accounts WHERE is_system = 0"
    )
    for acc in await cursor.fetchall():
        acc_id_to_key[acc["id"]] = {
            "bank_name": acc["bank_name"],
            "account_name": acc["account_name"],
            "account_number": acc["account_number"],
        }

    rules = []
    for r in rules_raw:
        cat_ref = cat_id_to_key.get(r["category_id"])
        if not cat_ref:
            continue
        rule_dict = {
            "search_text": r["search_text"],
            "match_type": r["match_type"],
            "category_name": cat_ref["name"],
            "category_type": cat_ref["type"],
            "priority": r["priority"],
            "applies_to": r["applies_to"],
        }
        if r.get("account_id"):
            acc_ref = acc_id_to_key.get(r["account_id"])
            if acc_ref:
                rule_dict["account_bank_name"] = acc_ref["bank_name"]
                rule_dict["account_name"] = acc_ref["account_name"]
                rule_dict["account_number"] = acc_ref["account_number"]
        rules.append(rule_dict)

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": _APP_NAME,
        "app_version": _APP_VERSION,
        "stats": {
            "bank_accounts": len(accounts),
            "categories": len(categories_to_export),
            "rules": len(rules),
        },
    }

    payload = {
        "version": _BACKUP_VERSION,
        "metadata": metadata,
        "data": {
            "bank_accounts": accounts,
            "categories": categories_to_export,
            "rules": rules,
        },
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _parse_backup(payload: dict) -> dict:
    version = payload.get("version", 1)
    if version not in (1, 2):
        raise ValueError(f"Unsupported backup version: {version}")

    if version == 2:
        metadata = payload.get("metadata", {})
        data = payload.get("data", {})
        return {
            "version": 2,
            "created_at": metadata.get("created_at", "unknown"),
            "stats": metadata.get("stats", {}),
            "accounts": data.get("bank_accounts", []),
            "categories": data.get("categories", []),
            "rules": data.get("rules", []),
        }
    else:
        return {
            "version": 1,
            "created_at": payload.get("exported_at", "unknown"),
            "stats": {
                "bank_accounts": len(payload.get("bank_accounts", [])),
                "categories": len(payload.get("categories", [])),
                "rules": len(payload.get("rules", [])),
            },
            "accounts": payload.get("bank_accounts", []),
            "categories": payload.get("categories", []),
            "rules": payload.get("rules", []),
        }


async def analyze_backup(db: aiosqlite.Connection, payload: dict) -> dict:
    backup = _parse_backup(payload)
    analysis = {
        "version": backup["version"],
        "created_at": backup["created_at"],
        "stats": backup["stats"],
        "accounts_to_import": [],
        "accounts_to_skip": [],
        "categories_to_import": [],
        "categories_to_skip": [],
        "rules_to_import": [],
        "rules_to_skip": [],
        "errors": [],
    }

    for acc in backup["accounts"]:
        cursor = await db.execute(
            "SELECT id FROM bank_accounts WHERE bank_name = ? AND account_name = ? AND account_number = ?",
            (acc["bank_name"], acc["account_name"], acc["account_number"]),
        )
        if await cursor.fetchone():
            analysis["accounts_to_skip"].append({
                "bank_name": acc["bank_name"],
                "account_name": acc["account_name"],
                "account_number": acc["account_number"],
                "reason": "already exists",
            })
        else:
            analysis["accounts_to_import"].append({
                "bank_name": acc["bank_name"],
                "account_name": acc["account_name"],
                "account_number": acc["account_number"],
            })

    for cat in backup["categories"]:
        cursor = await db.execute(
            "SELECT id FROM transaction_categories WHERE name = ? AND type = ?",
            (cat["name"], cat["type"]),
        )
        if await cursor.fetchone():
            analysis["categories_to_skip"].append({
                "name": cat["name"],
                "type": cat["type"],
                "reason": "already exists",
            })
        else:
            analysis["categories_to_import"].append({
                "name": cat["name"],
                "type": cat["type"],
            })

    cursor = await db.execute("SELECT id, name, type FROM transaction_categories")
    cat_lookup = {}
    for row in await cursor.fetchall():
        cat_lookup[(row["name"], row["type"])] = row["id"]

    for rule in backup["rules"]:
        cat_key = (rule["category_name"], rule["category_type"])
        cat_id = cat_lookup.get(cat_key)
        if not cat_id:
            cursor = await db.execute(
                "SELECT name, type FROM transaction_categories WHERE name LIKE ?",
                (f"%{rule['category_name']}%",),
            )
            similar = await cursor.fetchone()
            if similar:
                reason = f"category '{rule['category_name']}' not found (did you mean '{similar['name']}'?)"
            else:
                reason = f"category '{rule['category_name']} {rule['category_type']}' not found"
            analysis["errors"].append({
                "rule": f"{rule['search_text']} → {rule['category_name']}",
                "reason": reason,
            })
            analysis["rules_to_skip"].append({
                "search_text": rule["search_text"],
                "category": f"{rule['category_name']} ({rule['category_type']})",
                "priority": rule["priority"],
                "reason": reason,
            })
            continue
        account_id = None
        if rule.get("account_bank_name") and rule.get("account_name") and rule.get("account_number"):
            cursor = await db.execute(
                "SELECT id FROM bank_accounts WHERE bank_name = ? AND account_name = ? AND account_number = ?",
                (rule["account_bank_name"], rule["account_name"], rule["account_number"]),
            )
            acc_row = await cursor.fetchone()
            if acc_row:
                account_id = acc_row["id"]
        cursor = await db.execute(
            "SELECT id FROM classification_rules WHERE search_text = ? AND match_type = ? AND category_id = ? AND priority = ?",
            (rule["search_text"], rule["match_type"], cat_id, rule["priority"]),
        )
        if await cursor.fetchone():
            analysis["rules_to_skip"].append({
                "search_text": rule["search_text"],
                "category": f"{rule['category_name']} ({rule['category_type']})",
                "priority": rule["priority"],
                "reason": "already exists",
            })
        else:
            analysis["rules_to_import"].append({
                "search_text": rule["search_text"],
                "category": f"{rule['category_name']} ({rule['category_type']})",
                "priority": rule["priority"],
                "applies_to": rule.get("applies_to", "both"),
                "account_id": account_id,
            })

    return analysis


async def import_data(
    db: aiosqlite.Connection,
    payload: dict,
    sections: list[str] | None = None,
) -> dict:
    backup = _parse_backup(payload)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-6] + "Z"
    stats = {
        "accounts_created": 0,
        "categories_created": 0,
        "rules_created": 0,
        "skipped": {"accounts": 0, "categories": 0, "rules": 0},
        "errors": [],
    }

    if sections is None:
        sections = ["accounts", "categories", "rules"]

    if "accounts" in sections:
        await db.execute("BEGIN IMMEDIATE")
        try:
            for acc in backup["accounts"]:
                try:
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
                except aiosqlite.Error as e:
                    stats["errors"].append({
                        "section": "accounts",
                        "record": f"{acc.get('bank_name', '?')} - {acc.get('account_name', '?')}",
                        "error": str(e),
                    })
            await db.execute("COMMIT")
        except aiosqlite.Error:
            await db.execute("ROLLBACK")
            raise

    if "categories" in sections:
        await db.execute("BEGIN IMMEDIATE")
        try:
            for cat in backup["categories"]:
                try:
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
                except aiosqlite.Error as e:
                    stats["errors"].append({
                        "section": "categories",
                        "record": f"{cat.get('name', '?')} ({cat.get('type', '?')})",
                        "error": str(e),
                    })
            await db.execute("COMMIT")
        except aiosqlite.Error:
            await db.execute("ROLLBACK")
            raise

    if "rules" in sections:
        await db.execute("BEGIN IMMEDIATE")
        try:
            cursor = await db.execute("SELECT id, name, type FROM transaction_categories")
            cat_lookup = {}
            for row in await cursor.fetchall():
                cat_lookup[(row["name"], row["type"])] = row["id"]

            for rule in backup["rules"]:
                try:
                    cat_key = (rule["category_name"], rule["category_type"])
                    cat_id = cat_lookup.get(cat_key)
                    if not cat_id:
                        stats["skipped"]["rules"] += 1
                        stats["errors"].append({
                            "section": "rules",
                            "record": f"{rule.get('search_text', '?')} → {rule.get('category_name', '?')}",
                            "error": f"Category '{rule.get('category_name', '?')}' not found",
                        })
                        continue
                    account_id = None
                    if rule.get("account_bank_name") and rule.get("account_name") and rule.get("account_number"):
                        cursor = await db.execute(
                            "SELECT id FROM bank_accounts WHERE bank_name = ? AND account_name = ? AND account_number = ?",
                            (rule["account_bank_name"], rule["account_name"], rule["account_number"]),
                        )
                        acc_row = await cursor.fetchone()
                        if acc_row:
                            account_id = acc_row["id"]
                    cursor = await db.execute(
                        "SELECT id FROM classification_rules WHERE search_text = ? AND match_type = ? AND category_id = ? AND priority = ?",
                        (rule["search_text"], rule["match_type"], cat_id, rule["priority"]),
                    )
                    if await cursor.fetchone():
                        stats["skipped"]["rules"] += 1
                        continue
                    await db.execute(
                        """INSERT INTO classification_rules
                           (search_text, match_type, category_id, priority, applies_to, is_active, account_id, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)""",
                        (rule["search_text"], rule["match_type"], cat_id, rule["priority"],
                         rule.get("applies_to", "both"), account_id, now, now),
                    )
                    stats["rules_created"] += 1
                except aiosqlite.Error as e:
                    stats["errors"].append({
                        "section": "rules",
                        "record": f"{rule.get('search_text', '?')} → {rule.get('category_name', '?')}",
                        "error": str(e),
                    })
            await db.execute("COMMIT")
        except aiosqlite.Error:
            await db.execute("ROLLBACK")
            raise

    return stats

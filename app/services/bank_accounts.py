import aiosqlite
from datetime import datetime, timezone
from app.models.bank_accounts import BankAccountCreate


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return dict(row)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_account(db: aiosqlite.Connection, data: BankAccountCreate) -> dict:
    now = _now()
    cursor = await db.execute(
        """INSERT INTO bank_accounts
           (bank_name, account_name, account_number, ifsc_code, branch_name, notes, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
        (data.bank_name, data.account_name, data.account_number, data.ifsc_code,
         data.branch_name, data.notes, now, now),
    )
    await db.commit()
    return await get_account(db, cursor.lastrowid)


async def get_account(db: aiosqlite.Connection, account_id: int) -> dict | None:
    cursor = await db.execute("SELECT * FROM bank_accounts WHERE id = ?", (account_id,))
    return _row_to_dict(await cursor.fetchone())


async def list_accounts(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("SELECT * FROM bank_accounts ORDER BY created_at DESC")
    return [_row_to_dict(r) for r in await cursor.fetchall()]


async def toggle_account(db: aiosqlite.Connection, account_id: int) -> dict | None:
    account = await get_account(db, account_id)
    if not account:
        return None
    new_state = 0 if account["is_active"] else 1
    await db.execute(
        "UPDATE bank_accounts SET is_active = ?, updated_at = ? WHERE id = ?",
        (new_state, _now(), account_id),
    )
    await db.commit()
    return await get_account(db, account_id)


async def delete_account(db: aiosqlite.Connection, account_id: int) -> bool:
    cursor = await db.execute("DELETE FROM bank_accounts WHERE id = ?", (account_id,))
    await db.commit()
    return cursor.rowcount > 0


async def update_account(db: aiosqlite.Connection, account_id: int, data: dict) -> dict | None:
    existing = await get_account(db, account_id)
    if not existing:
        return None
    sets, vals = [], []
    for key in ("bank_name", "account_name", "account_number", "ifsc_code", "branch_name", "notes"):
        if key in data and data[key] is not None:
            sets.append(f"{key} = ?")
            vals.append(data[key])
    if not sets:
        return existing
    sets.append("updated_at = ?")
    vals.append(_now())
    vals.append(account_id)
    await db.execute(
        f"UPDATE bank_accounts SET {', '.join(sets)} WHERE id = ?",
        vals,
    )
    await db.commit()
    return await get_account(db, account_id)

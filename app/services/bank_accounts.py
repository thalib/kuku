import aiosqlite
from datetime import datetime, timezone
from app.models.bank_accounts import BankAccountCreate


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return dict(row)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_system_account(db: aiosqlite.Connection) -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM bank_accounts WHERE is_system = 1 AND bank_name = 'Cash In Hand' AND account_name = 'Petty Cash'"
    )
    return _row_to_dict(await cursor.fetchone())


async def ensure_cash_in_hand(db: aiosqlite.Connection) -> dict:
    existing = await get_system_account(db)
    if existing:
        return existing
    now = _now()
    cursor = await db.execute(
        """INSERT INTO bank_accounts
           (bank_name, account_name, account_number, ifsc_code, branch_name, notes,
            is_active, is_system, created_at, updated_at)
           VALUES ('Cash In Hand', 'Petty Cash', 'N/A', 'N/A', NULL, 'System petty cash account',
                   1, 1, ?, ?)""",
        (now, now),
    )
    await db.commit()

    from app.services.categories import create_transfer_categories

    try:
        await create_transfer_categories(db, 'Cash In Hand', 'Petty Cash')
        await db.commit()
    except aiosqlite.IntegrityError:
        pass

    return await get_account(db, cursor.lastrowid)


async def create_account(db: aiosqlite.Connection, data: BankAccountCreate) -> dict:
    now = _now()
    cursor = await db.execute(
        """INSERT INTO bank_accounts
           (bank_name, account_name, account_number, ifsc_code, branch_name, notes, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
        (data.bank_name, data.account_name, data.account_number, data.ifsc_code,
         data.branch_name, data.notes, now, now),
    )
    account_id = cursor.lastrowid

    from app.services.categories import create_transfer_categories

    try:
        await create_transfer_categories(db, data.bank_name, data.account_name)
    except aiosqlite.IntegrityError:
        # Transfer type not yet supported in database schema - silently ignore
        pass

    await db.commit()
    return await get_account(db, account_id)


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


async def count_transactions(db: aiosqlite.Connection, account_id: int) -> int:
    cursor = await db.execute(
        "SELECT COUNT(*) FROM bank_transactions WHERE account_id = ?",
        (account_id,),
    )
    row = await cursor.fetchone()
    return row[0]


async def delete_account(db: aiosqlite.Connection, account_id: int) -> bool:
    account = await get_account(db, account_id)
    if not account:
        return False
    if account.get("is_system", 0):
        return False

    from app.services.categories import delete_transfer_categories

    try:
        await delete_transfer_categories(db, account["bank_name"], account["account_name"])
    except aiosqlite.IntegrityError:
        pass

    cursor = await db.execute("DELETE FROM bank_accounts WHERE id = ?", (account_id,))
    await db.commit()
    return cursor.rowcount > 0


async def update_account(db: aiosqlite.Connection, account_id: int, data: dict) -> dict | None:
    existing = await get_account(db, account_id)
    if not existing:
        return None

    # Track if bank_name or account_name changed for transfer category update
    old_bank = existing.get("bank_name", "")
    old_account = existing.get("account_name", "")
    new_bank = data.get("bank_name", old_bank)
    new_account = data.get("account_name", old_account)

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

    if old_bank != new_bank or old_account != new_account:
        from app.services.categories import update_transfer_categories

        try:
            await update_transfer_categories(db, old_bank, old_account, new_bank, new_account)
        except aiosqlite.IntegrityError:
            pass

    await db.commit()
    return await get_account(db, account_id)

import aiosqlite
from datetime import datetime, timezone, date

from app.services import bank_accounts as bank_svc
from app.services import transactions as tx_svc


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_cash_account_id(db: aiosqlite.Connection) -> int:
    account = await bank_svc.get_system_account(db)
    if not account:
        raise ValueError("Cash In Hand system account not found")
    return account["id"]


async def list_transactions(db: aiosqlite.Connection, year: int, month: int) -> list[dict]:
    account_id = await get_cash_account_id(db)
    return await tx_svc.list_transactions(db, account_id, year, month)


async def get_summary(db: aiosqlite.Connection, year: int, month: int) -> dict:
    account_id = await get_cash_account_id(db)
    return await tx_svc.get_summary(db, account_id, year, month)


async def get_available_fy_years(db: aiosqlite.Connection) -> list[int]:
    account_id = await get_cash_account_id(db)
    return await tx_svc.get_available_fy_years(db, account_id)


async def get_available_months(db: aiosqlite.Connection, fy_start: int) -> list[int]:
    account_id = await get_cash_account_id(db)
    return await tx_svc.get_available_months(db, account_id, fy_start)


async def create_transaction(db: aiosqlite.Connection, data: dict) -> dict:
    account_id = await get_cash_account_id(db)
    now = _now()
    cursor = await db.execute(
        """INSERT INTO bank_transactions
           (account_id, txn_date, value_date, narration, reference, debit, credit, balance, category_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (account_id, data["txn_date"], data.get("value_date") or data["txn_date"],
         data.get("narration"), data.get("reference"),
         data.get("debit", 0), data.get("credit", 0),
         data.get("balance", 0), data.get("category_id"), now, now),
    )
    await db.commit()
    return await get_transaction(db, cursor.lastrowid)


async def get_transaction(db: aiosqlite.Connection, txn_id: int) -> dict | None:
    return await tx_svc.get_transaction_with_category(db, txn_id)


async def update_transaction(db: aiosqlite.Connection, txn_id: int, data: dict) -> dict | None:
    existing = await tx_svc.get_transaction(db, txn_id)
    if not existing:
        return None
    sets, vals = [], []
    field_map = {
        "txn_date": lambda v: v,
        "value_date": lambda v: v,
        "narration": lambda v: v,
        "reference": lambda v: v,
        "debit": lambda v: v,
        "credit": lambda v: v,
        "balance": lambda v: v,
        "category_id": lambda v: v,
    }
    for key, transform in field_map.items():
        if key in data:
            sets.append(f"{key} = ?")
            vals.append(transform(data[key]))
    if not sets:
        return existing
    sets.append("updated_at = ?")
    vals.append(_now())
    vals.append(txn_id)
    await db.execute(
        f"UPDATE bank_transactions SET {', '.join(sets)} WHERE id = ?",
        vals,
    )
    await db.commit()
    return await get_transaction(db, txn_id)


async def delete_transaction(db: aiosqlite.Connection, txn_id: int) -> bool:
    return await tx_svc.delete_transaction(db, txn_id)

import aiosqlite
from datetime import datetime, timezone
from app.models.categories import CategoryCreate, CategoryUpdate


def _transfer_label(bank_name: str, account_name: str) -> str:
    """Generate a consistent transfer label from bank and account name"""
    return f"{bank_name} - {account_name}"


SYSTEM_CATEGORIES = [
    ("Sales Revenue", "Income", "Revenue from sale of goods and products"),
    ("Service Revenue", "Income", "Revenue from services rendered"),
    ("Interest Income", "Income", "Interest earned on deposits and investments"),
    ("Rent Income", "Income", "Rental income received"),
    ("Commission Income", "Income", "Commission or brokerage earned"),
    ("Dividend Income", "Income", "Dividends received from investments"),
    ("Capital Gains", "Income", "Profit from sale of assets or investments"),
    ("Other Income", "Income", "Miscellaneous income not elsewhere classified"),
    ("Uncategorized Income", "Income", "(Default) Income not yet classified"),
    ("Cost of Goods Sold", "Expense", "Direct cost of goods sold or services delivered"),
    ("Salaries & Wages", "Expense", "Employee compensation and wages"),
    ("Payroll Taxes & Benefits", "Expense", "Employer contributions, PF, ESI, gratuity"),
    ("Rent & Lease", "Expense", "Rent for office, shop, plant or equipment"),
    ("Utilities", "Expense", "Electricity, water, gas and other utilities"),
    ("Telephone & Internet", "Expense", "Telephone, mobile and internet charges"),
    ("Advertising & Marketing", "Expense", "Advertising, promotion and marketing costs"),
    ("Insurance", "Expense", "Business insurance premiums"),
    ("Office Supplies", "Expense", "Stationery, consumables and office supplies"),
    ("Professional Fees", "Expense", "Legal, accounting, auditing and consulting fees"),
    ("Travel & Conveyance", "Expense", "Business travel, fuel and conveyance expenses"),
    ("Repairs & Maintenance", "Expense", "Repairs and maintenance of assets and premises"),
    ("Bank Charges", "Expense", "Bank fees, merchant charges and processing fees"),
    ("Interest Paid", "Expense", "Interest on loans, overdrafts and borrowings"),
    ("Depreciation", "Expense", "Depreciation of fixed assets"),
    ("Tax Expense", "Expense", "Direct taxes paid (income tax, property tax)"),
    ("Shipping & Transport", "Expense", "Freight, carriage, delivery and logistics charges"),
    ("Shipping & Transport", "Income", "Shipping and logistics charges billed to customers"),
    ("Miscellaneous Expense", "Expense", "Other expenses not elsewhere classified"),
    ("Uncategorized Expense", "Expense", "(Default) Expense not yet classified"),
    ("Cash & Bank", "Asset", "Cash in hand and balances in bank accounts"),
    ("Accounts Receivable", "Asset", "Money owed by customers and trade debtors"),
    ("Inventory", "Asset", "Stock in hand, raw materials, work in progress"),
    ("Fixed Assets", "Asset", "Property, plant, equipment and machinery"),
    ("Investments", "Asset", "Financial investments, shares, bonds and deposits"),
    ("Accounts Payable", "Liability", "Money owed to suppliers and trade creditors"),
    ("Short-term Loans", "Liability", "Loans and borrowings due within one year"),
    ("Long-term Loans", "Liability", "Loans and borrowings due beyond one year"),
    ("Credit Card Payable", "Liability", "Outstanding credit card balances"),
    ("Tax Payable", "Liability", "GST, TDS and other tax liabilities payable"),
    ("Advances Received", "Liability", "Customer advances and unearned revenue"),
    ("Owner Capital", "Equity", "Capital invested by the owner or partners"),
    ("Retained Earnings", "Equity", "Accumulated profits retained in business"),
    ("Owner Drawings", "Equity", "Money withdrawn by owner for personal use"),
]


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    return dict(row)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_categories(db: aiosqlite.Connection) -> int:
    cursor = await db.execute(
        "SELECT name, type FROM transaction_categories WHERE is_system = 1"
    )
    existing = {(row["name"], row["type"]) for row in await cursor.fetchall()}
    expected = len(SYSTEM_CATEGORIES)
    if len(existing) >= expected:
        return 0
    now = _now()
    inserted = 0
    for name, ctype, desc in SYSTEM_CATEGORIES:
        if (name, ctype) not in existing:
            await db.execute(
                """INSERT INTO transaction_categories
                   (name, type, description, is_system, created_at, updated_at)
                   VALUES (?, ?, ?, 1, ?, ?)""",
                (name, ctype, desc, now, now),
            )
            inserted += 1
    return inserted


async def create_category(db: aiosqlite.Connection, data: CategoryCreate) -> dict:
    now = _now()
    cursor = await db.execute(
        """INSERT INTO transaction_categories
           (name, type, description, is_system, created_at, updated_at)
           VALUES (?, ?, ?, 0, ?, ?)""",
        (data.name, data.type, data.description, now, now),
    )
    await db.commit()
    return await get_category(db, cursor.lastrowid)


async def get_category(db: aiosqlite.Connection, category_id: int) -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM transaction_categories WHERE id = ?", (category_id,)
    )
    return _row_to_dict(await cursor.fetchone())


async def list_categories(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM transaction_categories ORDER BY type, is_system DESC, name"
    )
    return [_row_to_dict(r) for r in await cursor.fetchall()]


async def count_transactions(db: aiosqlite.Connection, category_id: int) -> int:
    cursor = await db.execute(
        "SELECT COUNT(*) FROM bank_transactions WHERE category_id = ?",
        (category_id,),
    )
    row = await cursor.fetchone()
    return row[0]


async def delete_category(db: aiosqlite.Connection, category_id: int) -> bool:
    cursor = await db.execute(
        "DELETE FROM transaction_categories WHERE id = ? AND is_system = 0",
        (category_id,),
    )
    await db.commit()
    return cursor.rowcount > 0


async def update_category(
    db: aiosqlite.Connection, category_id: int, data: CategoryUpdate
) -> dict | None:
    sets, vals = [], []
    for key in ("name", "type", "description"):
        val = getattr(data, key)
        if val is not None:
            sets.append(f"{key} = ?")
            vals.append(val)
    if not sets:
        return await get_category(db, category_id)
    sets.append("updated_at = ?")
    vals.append(_now())
    vals.append(category_id)
    cursor = await db.execute(
        f"UPDATE transaction_categories SET {', '.join(sets)} WHERE id = ? AND is_system = 0",
        vals,
    )
    await db.commit()
    if cursor.rowcount == 0:
        return None
    return await get_category(db, category_id)


async def create_transfer_categories(
    db: aiosqlite.Connection,
    bank_name: str,
    account_name: str,
) -> tuple[int, int]:
    """Create 'to' and 'from' transfer categories for a bank account.

    Returns (to_category_id, from_category_id).
    """
    label = _transfer_label(bank_name, account_name)
    now = _now()

    to_id = await _insert_transfer_category(db, f"to {label}", now)
    from_id = await _insert_transfer_category(db, f"from {label}", now)

    return to_id, from_id


async def _insert_transfer_category(
    db: aiosqlite.Connection,
    name: str,
    now: str,
) -> int:
    cursor = await db.execute(
        """INSERT INTO transaction_categories
           (name, type, description, is_system, created_at, updated_at)
           VALUES (?, 'Transfer', ?, 1, ?, ?)""",
        (name, f"Internal transfer {name}", now, now),
    )
    return cursor.lastrowid


async def delete_transfer_categories(
    db: aiosqlite.Connection,
    bank_name: str,
    account_name: str,
) -> int:
    """Delete transfer categories for a specific bank account.

    Returns the count of deleted categories.
    """
    label = _transfer_label(bank_name, account_name)
    cursor = await db.execute(
        """DELETE FROM transaction_categories
           WHERE is_system = 1 AND type = 'Transfer'
             AND (name = 'to ' || ? OR name = 'from ' || ?)""",
        (label, label),
    )
    await db.commit()
    return cursor.rowcount


async def update_transfer_categories(
    db: aiosqlite.Connection,
    old_bank_name: str,
    old_account_name: str,
    new_bank_name: str,
    new_account_name: str,
) -> int:
    """Rename transfer categories when an account is updated.

    Returns the count of updated categories.
    """
    old_label = _transfer_label(old_bank_name, old_account_name)
    new_label = _transfer_label(new_bank_name, new_account_name)

    if old_label == new_label:
        return 0

    now = _now()
    cursor = await db.execute(
        f"""UPDATE transaction_categories
           SET name = REPLACE(name, 'to {old_label}', 'to {new_label}'),
               updated_at = ?
           WHERE is_system = 1 AND type = 'Transfer'
             AND name = 'to {old_label}'""",
        (now,),
    )
    cursor2 = await db.execute(
        f"""UPDATE transaction_categories
           SET name = REPLACE(name, 'from {old_label}', 'from {new_label}'),
               updated_at = ?
           WHERE is_system = 1 AND type = 'Transfer'
             AND name = 'from {old_label}'""",
        (now,),
    )
    await db.commit()
    return cursor.rowcount + cursor2.rowcount


async def list_transfer_categories(
    db: aiosqlite.Connection,
) -> list[dict]:
    """Get all transfer categories, ordered by name."""
    cursor = await db.execute(
        """SELECT id, name, type
           FROM transaction_categories
           WHERE is_system = 1 AND type = 'Transfer'
           ORDER BY name"""
    )
    return [_row_to_dict(r) for r in await cursor.fetchall()]

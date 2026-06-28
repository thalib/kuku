import aiosqlite

FY_MONTHS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]

MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def _fy_date_range(fy_start: int, month: int | None = None) -> tuple[str, str]:
    if month is not None:
        cal_year = fy_start if month >= 4 else fy_start + 1
        start = f"{cal_year:04d}-{month:02d}-01"
        if month == 12:
            end = f"{fy_start + 1:04d}-01-01"
        else:
            next_month = month + 1
            end = f"{cal_year:04d}-{next_month:02d}-01"
    else:
        start = f"{fy_start:04d}-04-01"
        end = f"{fy_start + 1:04d}-04-01"
    return start, end


async def get_available_fy_years(db: aiosqlite.Connection) -> list[int]:
    cursor = await db.execute("""
        SELECT DISTINCT
            CASE WHEN CAST(strftime('%m', txn_date) AS INTEGER) >= 4
                 THEN CAST(strftime('%Y', txn_date) AS INTEGER)
                 ELSE CAST(strftime('%Y', txn_date) AS INTEGER) - 1
            END AS fy_start
        FROM bank_transactions
        ORDER BY fy_start
    """)
    return [int(r[0]) for r in await cursor.fetchall()]


async def get_available_months(db: aiosqlite.Connection, fy_start: int) -> list[int]:
    cursor = await db.execute("""
        SELECT DISTINCT CAST(strftime('%m', txn_date) AS INTEGER) AS m
        FROM bank_transactions
        WHERE (CAST(strftime('%m', txn_date) AS INTEGER) >= 4
               AND strftime('%Y', txn_date) = CAST(? AS TEXT))
           OR (CAST(strftime('%m', txn_date) AS INTEGER) < 4
               AND strftime('%Y', txn_date) = CAST(? AS TEXT))
        ORDER BY m
    """, (fy_start, fy_start + 1))
    return [int(r[0]) for r in await cursor.fetchall()]


async def get_accounts_with_balance(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("""
        SELECT a.id, a.bank_name, a.account_name, a.account_number, a.is_active,
               COALESCE(
                   (SELECT t.balance FROM bank_transactions t
                    WHERE t.account_id = a.id
                    ORDER BY t.txn_date DESC, t.id DESC LIMIT 1),
                   0
               ) AS last_balance
        FROM bank_accounts a
        ORDER BY a.created_at DESC
    """)
    return [dict(r) for r in await cursor.fetchall()]


async def get_income_expense_by_month(
    db: aiosqlite.Connection, fy_start: int, month: int | None = None
) -> list[dict]:
    start_date, end_date = _fy_date_range(fy_start, month)

    if month is not None:
        cal_year = fy_start if month >= 4 else fy_start + 1
        cursor = await db.execute("""
            SELECT
                COALESCE(SUM(credit), 0) AS total_income,
                COALESCE(SUM(debit), 0) AS total_expense
            FROM bank_transactions
            WHERE txn_date >= ? AND txn_date < ?
        """, (start_date, end_date))
        row = await cursor.fetchone()
        return [{
            "month": month,
            "label": f"{MONTH_NAMES[month]} {cal_year}",
            "income": round(row["total_income"], 2),
            "expense": round(row["total_expense"], 2),
        }]

    fy_start_date = f"{fy_start:04d}-04-01"
    fy_end_date = f"{fy_start + 1:04d}-04-01"

    cursor = await db.execute("""
        SELECT strftime('%Y-%m', txn_date) AS ym,
               COALESCE(SUM(credit), 0) AS total_income,
               COALESCE(SUM(debit), 0) AS total_expense
        FROM bank_transactions
        WHERE txn_date >= ? AND txn_date < ?
        GROUP BY ym
        ORDER BY ym
    """, (fy_start_date, fy_end_date))

    by_ym = {r["ym"]: r for r in await cursor.fetchall()}

    results = []
    for m in FY_MONTHS:
        cal_year = fy_start if m >= 4 else fy_start + 1
        ym_key = f"{cal_year:04d}-{m:02d}"
        row = by_ym.get(ym_key)
        results.append({
            "month": m,
            "label": f"{MONTH_NAMES[m]} {cal_year}",
            "income": round(row["total_income"], 2) if row else 0,
            "expense": round(row["total_expense"], 2) if row else 0,
        })
    return results


async def get_top_categories(
    db: aiosqlite.Connection,
    fy_start: int,
    category_type: str,
    month: int | None = None,
    limit: int = 5,
) -> list[dict]:
    start_date, end_date = _fy_date_range(fy_start, month)
    column = "credit" if category_type == "Income" else "debit"

    cursor = await db.execute(f"""
        SELECT c.name AS category,
               COALESCE(SUM(t.{column}), 0) AS total
        FROM bank_transactions t
        JOIN transaction_categories c ON t.category_id = c.id
        WHERE t.txn_date >= ? AND t.txn_date < ?
          AND c.type = ?
          AND t.{column} > 0
        GROUP BY c.id, c.name
        ORDER BY total DESC
        LIMIT ?
    """, (start_date, end_date, category_type, limit))
    return [{"category": r["category"], "total": round(r["total"], 2)} for r in await cursor.fetchall()]


async def get_top_income_categories(
    db: aiosqlite.Connection, fy_start: int, month: int | None = None, limit: int = 5
) -> list[dict]:
    return await get_top_categories(db, fy_start, "Income", month, limit)


async def get_top_expense_categories(
    db: aiosqlite.Connection, fy_start: int, month: int | None = None, limit: int = 5
) -> list[dict]:
    return await get_top_categories(db, fy_start, "Expense", month, limit)


async def get_dashboard_data(
    db: aiosqlite.Connection, fy_start: int, month: int | None = None
) -> dict:
    accounts = await get_accounts_with_balance(db)
    monthly_data = await get_income_expense_by_month(db, fy_start, month)
    top_income = await get_top_income_categories(db, fy_start, month)
    top_expense = await get_top_expense_categories(db, fy_start, month)

    total_income = sum(m["income"] for m in monthly_data)
    total_expense = sum(m["expense"] for m in monthly_data)

    return {
        "accounts": accounts,
        "monthly_data": monthly_data,
        "top_income": top_income,
        "top_expense": top_expense,
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "net": round(total_income - total_expense, 2),
    }

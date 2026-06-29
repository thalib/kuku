import aiosqlite
from datetime import datetime

from app.services.dashboard import get_available_fy_years, _fy_date_range, MONTH_NAMES, FY_MONTHS


def _get_current_fy() -> int:
    today = datetime.now()
    return today.year if today.month >= 4 else today.year - 1


async def get_report_fy_years(db: aiosqlite.Connection) -> list[int]:
    years = await get_available_fy_years(db)
    if not years:
        current_fy = _get_current_fy()
        years = [current_fy - 1, current_fy, current_fy + 1]
    return sorted(years)


async def _get_category_totals_by_type(
    db: aiosqlite.Connection,
    start_date: str,
    end_date: str,
    category_types: list[str],
) -> dict[str, list[dict]]:
    placeholders = ",".join(["?"] * len(category_types))
    cursor = await db.execute(f"""
        SELECT c.id, c.name, c.type,
               COALESCE(SUM(t.credit), 0) AS total_credit,
               COALESCE(SUM(t.debit), 0) AS total_debit
        FROM bank_transactions t
        JOIN transaction_categories c ON t.category_id = c.id
        WHERE t.txn_date >= ? AND t.txn_date < ?
          AND c.type IN ({placeholders})
          AND c.type != 'Transfer'
        GROUP BY c.id, c.name, c.type
        ORDER BY c.type, c.name
    """, (start_date, end_date, *category_types))

    result: dict[str, list[dict]] = {}
    for row in await cursor.fetchall():
        cat_type = row["type"]
        if cat_type not in result:
            result[cat_type] = []
        result[cat_type].append({
            "id": row["id"],
            "name": row["name"],
            "type": cat_type,
            "total_credit": round(row["total_credit"], 2),
            "total_debit": round(row["total_debit"], 2),
        })
    return result


async def _get_cumulative_category_totals(
    db: aiosqlite.Connection,
    end_date: str,
    category_types: list[str],
) -> dict[str, list[dict]]:
    placeholders = ",".join(["?"] * len(category_types))
    cursor = await db.execute(f"""
        SELECT c.id, c.name, c.type,
               COALESCE(SUM(t.credit), 0) AS total_credit,
               COALESCE(SUM(t.debit), 0) AS total_debit
        FROM bank_transactions t
        JOIN transaction_categories c ON t.category_id = c.id
        WHERE t.txn_date < ?
          AND c.type IN ({placeholders})
          AND c.type != 'Transfer'
        GROUP BY c.id, c.name, c.type
        ORDER BY c.type, c.name
    """, (end_date, *category_types))

    result: dict[str, list[dict]] = {}
    for row in await cursor.fetchall():
        cat_type = row["type"]
        if cat_type not in result:
            result[cat_type] = []
        result[cat_type].append({
            "id": row["id"],
            "name": row["name"],
            "type": cat_type,
            "total_credit": round(row["total_credit"], 2),
            "total_debit": round(row["total_debit"], 2),
        })
    return result


async def _get_bank_balances_as_of(db: aiosqlite.Connection, as_of_date: str) -> list[dict]:
    cursor = await db.execute("""
        SELECT a.id, a.bank_name, a.account_name, a.account_number,
               COALESCE(
                   (SELECT t.balance FROM bank_transactions t
                    WHERE t.account_id = a.id AND t.txn_date < ?
                    ORDER BY t.txn_date DESC, t.id DESC LIMIT 1),
                    0
                ) AS balance
        FROM bank_accounts a
        WHERE a.is_active = 1
        ORDER BY a.bank_name, a.account_name
    """, (as_of_date,))
    return [dict(r) for r in await cursor.fetchall()]


async def _get_opening_balances_for_fy(
    db: aiosqlite.Connection, fy_start_date: str
) -> list[dict]:
    """Opening balance per account for cash-flow reports.

    If no transaction exists before the FY start, the opening balance is
    derived from the very first recorded transaction using:
        opening = first_txn.balance - first_txn.credit + first_txn.debit
    Falls back to 0 when the account has no transactions at all.
    """
    cursor = await db.execute("""
        SELECT a.id, a.bank_name, a.account_name, a.account_number,
            COALESCE(
                (SELECT t.balance FROM bank_transactions t
                 WHERE t.account_id = a.id AND t.txn_date < ?
                 ORDER BY t.txn_date DESC, t.id DESC LIMIT 1),
                COALESCE(
                    (SELECT t.balance - t.credit + t.debit FROM bank_transactions t
                     WHERE t.account_id = a.id
                     ORDER BY t.txn_date ASC, t.id ASC LIMIT 1),
                    0
                )
            ) AS balance
        FROM bank_accounts a
        WHERE a.is_active = 1
        ORDER BY a.bank_name, a.account_name
    """, (fy_start_date,))
    return [dict(r) for r in await cursor.fetchall()]


async def get_profit_loss(db: aiosqlite.Connection, fy_start: int) -> dict:
    start_date, end_date = _fy_date_range(fy_start)

    category_types = ["Income", "Expense"]
    data = await _get_category_totals_by_type(db, start_date, end_date, category_types)

    income_categories = data.get("Income", [])
    expense_categories = data.get("Expense", [])

    total_income = 0.0
    income_items = []
    for cat in income_categories:
        amount = cat["total_credit"]
        if amount > 0:
            income_items.append({"name": cat["name"], "amount": amount})
            total_income += amount

    total_expense = 0.0
    expense_items = []
    for cat in expense_categories:
        amount = cat["total_debit"]
        if amount > 0:
            expense_items.append({"name": cat["name"], "amount": amount})
            total_expense += amount

    total_income = round(total_income, 2)
    total_expense = round(total_expense, 2)
    net_profit = round(total_income - total_expense, 2)

    return {
        "fy_start": fy_start,
        "fy_label": f"FY {fy_start}-{fy_start + 1}",
        "period_from": start_date,
        "period_to": end_date,
        "income_categories": income_items,
        "expense_categories": expense_items,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": net_profit,
        "is_profit": net_profit >= 0,
    }


async def get_balance_sheet(db: aiosqlite.Connection, fy_start: int) -> dict:
    start_date, end_date = _fy_date_range(fy_start)

    bank_balances = await _get_bank_balances_as_of(db, end_date)
    total_cash_at_bank = round(sum(b["balance"] for b in bank_balances), 2)

    cumulative_data = await _get_cumulative_category_totals(
        db, end_date, ["Asset", "Liability", "Equity", "Income", "Expense"]
    )

    asset_categories = cumulative_data.get("Asset", [])
    liability_categories = cumulative_data.get("Liability", [])
    equity_categories = cumulative_data.get("Equity", [])
    income_categories = cumulative_data.get("Income", [])
    expense_categories = cumulative_data.get("Expense", [])

    other_assets = []
    total_other_assets = 0.0
    for cat in asset_categories:
        net = round(cat["total_debit"] - cat["total_credit"], 2)
        if net != 0:
            other_assets.append({"name": cat["name"], "amount": net})
            total_other_assets += net
    total_other_assets = round(total_other_assets, 2)

    total_assets = round(total_cash_at_bank + total_other_assets, 2)

    liabilities = []
    total_liabilities = 0.0
    for cat in liability_categories:
        net = round(cat["total_credit"] - cat["total_debit"], 2)
        if net != 0:
            liabilities.append({"name": cat["name"], "amount": net})
            total_liabilities += net
    total_liabilities = round(total_liabilities, 2)

    equity_items = []
    total_equity = 0.0
    for cat in equity_categories:
        net = round(cat["total_credit"] - cat["total_debit"], 2)
        if net != 0:
            equity_items.append({"name": cat["name"], "amount": net})
            total_equity += net

    cumulative_income = round(sum(c["total_credit"] for c in income_categories), 2)
    cumulative_expense = round(sum(c["total_debit"] for c in expense_categories), 2)
    retained_earnings = round(cumulative_income - cumulative_expense, 2)

    if retained_earnings != 0:
        equity_items.append({"name": "Retained Earnings", "amount": retained_earnings})
    total_equity = round(total_equity + retained_earnings, 2)

    total_liabilities_equity = round(total_liabilities + total_equity, 2)

    return {
        "fy_start": fy_start,
        "fy_label": f"FY {fy_start}-{fy_start + 1}",
        "as_on": end_date,
        "bank_balances": bank_balances,
        "total_cash_at_bank": total_cash_at_bank,
        "other_assets": other_assets,
        "total_other_assets": total_other_assets,
        "total_assets": total_assets,
        "liabilities": liabilities,
        "total_liabilities": total_liabilities,
        "equity_items": equity_items,
        "total_equity": total_equity,
        "total_liabilities_equity": total_liabilities_equity,
        "is_balanced": abs(total_assets - total_liabilities_equity) < 0.01,
    }


async def get_cash_flow(db: aiosqlite.Connection, fy_start: int) -> dict:
    start_date, end_date = _fy_date_range(fy_start)

    category_types = ["Income", "Expense", "Asset", "Liability", "Equity"]
    data = await _get_category_totals_by_type(db, start_date, end_date, category_types)

    income_cats = data.get("Income", [])
    expense_cats = data.get("Expense", [])
    asset_cats = data.get("Asset", [])
    liability_cats = data.get("Liability", [])
    equity_cats = data.get("Equity", [])

    operating_inflows = 0.0
    operating_inflow_items = []
    for cat in income_cats:
        amt = cat["total_credit"]
        if amt > 0:
            operating_inflow_items.append({"name": cat["name"], "amount": amt})
            operating_inflows += amt

    operating_outflows = 0.0
    operating_outflow_items = []
    for cat in expense_cats:
        amt = cat["total_debit"]
        if amt > 0:
            operating_outflow_items.append({"name": cat["name"], "amount": amt})
            operating_outflows += amt

    operating_inflows = round(operating_inflows, 2)
    operating_outflows = round(operating_outflows, 2)
    net_operating = round(operating_inflows - operating_outflows, 2)

    investing_outflows = 0.0
    investing_outflow_items = []
    investing_inflows = 0.0
    investing_inflow_items = []
    for cat in asset_cats:
        debit = cat["total_debit"]
        credit = cat["total_credit"]
        if debit > 0:
            investing_outflow_items.append({"name": cat["name"], "amount": debit})
            investing_outflows += debit
        if credit > 0:
            investing_inflow_items.append({"name": cat["name"], "amount": credit})
            investing_inflows += credit

    investing_outflows = round(investing_outflows, 2)
    investing_inflows = round(investing_inflows, 2)
    net_investing = round(investing_inflows - investing_outflows, 2)

    financing_inflows = 0.0
    financing_inflow_items = []
    financing_outflows = 0.0
    financing_outflow_items = []
    for cat in liability_cats:
        credit = cat["total_credit"]
        debit = cat["total_debit"]
        if credit > 0:
            financing_inflow_items.append({"name": cat["name"], "amount": credit})
            financing_inflows += credit
        if debit > 0:
            financing_outflow_items.append({"name": cat["name"], "amount": debit})
            financing_outflows += debit
    for cat in equity_cats:
        credit = cat["total_credit"]
        debit = cat["total_debit"]
        if credit > 0:
            financing_inflow_items.append({"name": cat["name"], "amount": credit})
            financing_inflows += credit
        if debit > 0:
            financing_outflow_items.append({"name": cat["name"], "amount": debit})
            financing_outflows += debit

    financing_inflows = round(financing_inflows, 2)
    financing_outflows = round(financing_outflows, 2)
    net_financing = round(financing_inflows - financing_outflows, 2)

    net_change = round(net_operating + net_investing + net_financing, 2)

    opening_balances = await _get_opening_balances_for_fy(db, start_date)
    closing_balances = await _get_bank_balances_as_of(db, end_date)
    opening_cash = round(sum(b["balance"] for b in opening_balances), 2)
    closing_cash = round(sum(b["balance"] for b in closing_balances), 2)

    return {
        "fy_start": fy_start,
        "fy_label": f"FY {fy_start}-{fy_start + 1}",
        "period_from": start_date,
        "period_to": end_date,
        "operating_inflow_items": operating_inflow_items,
        "operating_inflows": operating_inflows,
        "operating_outflow_items": operating_outflow_items,
        "operating_outflows": operating_outflows,
        "net_operating": net_operating,
        "investing_outflow_items": investing_outflow_items,
        "investing_outflows": investing_outflows,
        "investing_inflow_items": investing_inflow_items,
        "investing_inflows": investing_inflows,
        "net_investing": net_investing,
        "financing_inflow_items": financing_inflow_items,
        "financing_inflows": financing_inflows,
        "financing_outflow_items": financing_outflow_items,
        "financing_outflows": financing_outflows,
        "net_financing": net_financing,
        "net_change": net_change,
        "opening_cash": opening_cash,
        "closing_cash": closing_cash,
        "bank_balances": closing_balances,
    }

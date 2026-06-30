# SPEC.md

## Overview

`kuku` is "Kuku" — a desktop-web hybrid business application built with Python.

### Sidebar Navigation Groups

| Group   | Link           | URL                          |
|---------|----------------|------------------------------|
|         | Dashboard      | /                            |
| BANKS   | Accounts       | /banks/accounts              |
| BANKS   | Transaction    | /banks/transactions          |
| BANKS   | Categories     | /banks/categories            |
| BANKS   | Rules          | /banks/rules                 |
| REPORTS | Profit & Loss  | /reports/profit-loss         |
| REPORTS | Balance Sheet  | /reports/balance-sheet       |
| REPORTS | Cash Flow      | /reports/cash-flow           |
| ADMIN   | Backup         | /backup                      |

### Configuration

Settings are loaded from a `.env` file in the project root (see `.env.example` for reference). `app/config.py` uses `python-dotenv` to load environment variables at startup.

| Variable       | Required | Default | Notes                                  |
|----------------|----------|---------|----------------------------------------|
| COMPANY_NAME   | no       | "Kuku"  | Displayed in export headers and reports |

Additional settings will be added here as the application grows.

## Dashboard

**URL**: `/`
**Purpose**: Financial overview of the organisation. Shows bank account balances, income vs. expense trends, and top income/expense category breakdowns. Data is driven entirely from bank transaction records.

### Period Selector

- Financial Year dropdown: lists FY years with transaction data (e.g. "FY 2025-2026").
- Month dropdown: optional filter within the selected FY. Defaults to "All Months" when no month is selected.
- Update button: submits the selected period via HTMX; replaces the dashboard content area without full page reload.
- When no transaction data exists, a placeholder message is shown instead of charts/tables.

### Summary Cards

Three cards displayed in a row: Total Income, Total Expense, Net (income - expense).
- Total Income: green text.
- Total Expense: red text.
- Net: green if positive, red if negative.

### Bank Accounts Table

- Columns: Bank Name | Account Name | Account No. (last 4 digits) | Last Balance | Status
- Last Balance: taken from the most recent transaction for each account; 0 if no transactions.
- Status: green "Active" badge or grey "Inactive" badge.
- Follows Bootstrap compact table style (`table-sm table-hover align-middle`).

### Charts

Charts rendered with Chart.js 4 (CDN). Three charts below the summary/table:

1. **Income & Expense (Bar Chart)**: grouped bar chart showing monthly income (green) and expense (red) for the selected period. X-axis shows months in FY order (Apr→Mar).
2. **Top Income Sources (Pie Chart)**: top 5 income categories by total credit amount.
3. **Top Expense Categories (Pie Chart)**: top 5 expense categories by total debit amount.

### Financial Year

- Follows Indian accounting standard same as Transactions: FY runs April to March.
- FY parameter uses the start year (e.g. `fy=2025` for FY 2025-26).
- Month uses calendar month number (4=Apr, 3=Mar).

### Modular Architecture

- **Service**: `app/services/dashboard.py` — pure data aggregation functions designed for reuse in future reports (Profit & Loss, Cash Flow, Balance Sheet).
  - `get_available_fy_years(db)` — lists all FY years with transactions.
  - `get_available_months(db, fy_start)` — lists months with data for a given FY.
  - `get_accounts_with_balance(db)` — all accounts with their latest closing balance.
  - `get_income_expense_by_month(db, fy_start, month=None)` — monthly income/expense data.
  - `get_top_categories(db, fy_start, category_type, month=None, limit=5)` — top categories by amount.
  - `get_dashboard_data(db, fy_start, month=None)` — composite function returning all dashboard data.
- **Router**: `app/routers/dashboard.py` — `GET /` for the full page, `GET /content` for the HTMX partial.
- **Templates**: `pages/dashboard.html` (extends base, HTMX loads content) + `partials/dashboard_content.html` (charts, tables, filter form).

### Routes

| Method | URL                              | Purpose                         |
|--------|----------------------------------|---------------------------------|
| GET    | /                                | Full dashboard page             |
| GET    | /content?fy=&month=              | Dashboard content partial (HTMX)|

## Reports

Three financial reports generated on demand from transaction and category data. Indian accounting standards (ICAI) format.

### On-Demand Generation Flow

1. User opens report page — no data loaded, shows empty state with FY selector
2. FY dropdown populated via `/reports/fy-years` (lightweight JSON, no report computed)
3. User selects Financial Year, clicks **Generate Report**
4. Progress bar (animated Bootstrap `.progress-bar`) appears; button shows spinner
5. HTMX `GET /reports/<report>/content?fy=<year>` returns the report HTML
6. Report rendered in-place; progress bar hidden; button re-enabled
7. **Download PDF** button appears in the report header

### Profit & Loss Account

**URL**: `/reports/profit-loss`
**Purpose**: Income vs Expense summary for the selected FY. Shows Net Profit or Net Loss.

- Header: company name, "Profit and Loss", period (Apr 1 to Mar 31)
- Income section: all Income-type categories with total credits
- Expense section: all Expense-type categories with total debits
- Net Profit/Loss: total income minus total expenses
- Transfers excluded (internal movements, not income/expense)

### Balance Sheet

**URL**: `/reports/balance-sheet`
**Purpose**: Snapshot of Assets, Liabilities, and Equity at the end of the FY.

- Header: company name, "Balance Sheet", "As on" date (end of FY)
- Assets: Cash & Bank balances (from latest transaction per account), other Asset-type categories (debit minus credit)
- Liabilities: Liability-type categories (credit minus debit)
- Equity: Equity-type categories (credit minus debit) + cumulative Retained Earnings
- Balance check: shows ✅ if Assets = Liabilities + Equity, ⚠️ with difference amount if not

### Cash Flow Statement

**URL**: `/reports/cash-flow`
**Purpose**: Movement of cash categorized by Operating, Investing, and Financing activities per Ind AS 7.

- Operating: Income (inflows) and Expenses (outflows)
- Investing: Asset category debits (purchases) and credits (disposals)
- Financing: Liability and Equity credits (inflows like loans/capital) and debits (outflows like repayments/drawings)
- Net cash flow = Operating + Investing + Financing
- Summary cards: Opening Cash, Net Change, Closing Cash (bank balance at FY end)
- Opening Cash: for each account, uses the last known balance before FY start. If no transactions exist before FY start, the opening is derived from the first recorded transaction: `opening = first_txn.balance - first_txn.credit + first_txn.debit`. Falls back to 0 when an account has no transactions at all.
- Closing Cash by Account table

### Financial Year

- Follows Indian FY: April to March. Parameter uses start year (`fy=2025` → FY 2025-26).
- FY dropdown is populated on page load from actual transaction data.

### PDF Export

Each report has a PDF export reusing the xhtml2pdf pattern from Bank Transactions:
- Template: `app/templates/exports/reports/<report>/pdf.html`
- A4 portrait, company header, period label, styled report tables, "Page X of Y" footer

### Modular Architecture

- **Service**: `app/services/reports.py` — pure computation from transactions/categories
  - `get_profit_loss(db, fy_start)` → income/expense categories and net profit
  - `get_balance_sheet(db, fy_start)` → assets, liabilities, equity, balance check
  - `get_cash_flow(db, fy_start)` → operating/investing/financing cash flows
  - `get_report_fy_years(db)` → available FY years
- **Router**: `app/routers/reports.py` — page routes, content (HTMX) routes, PDF streams, FY years JSON

### Routes

| Method | URL                                | Purpose                          |
|--------|------------------------------------|----------------------------------|
| GET    | /reports                           | Redirect → /reports/profit-loss   |
| GET    | /reports/fy-years                  | Available FY years (JSON)         |
| GET    | /reports/profit-loss               | P&L page                          |
| GET    | /reports/profit-loss/content?fy=   | P&L content (HTMX)                |
| GET    | /reports/profit-loss/pdf?fy=       | P&L PDF download                  |
| GET    | /reports/balance-sheet             | Balance Sheet page                |
| GET    | /reports/balance-sheet/content?fy= | Balance Sheet content (HTMX)      |
| GET    | /reports/balance-sheet/pdf?fy=     | Balance Sheet PDF download        |
| GET    | /reports/cash-flow                 | Cash Flow page                    |
| GET    | /reports/cash-flow/content?fy=     | Cash Flow content (HTMX)          |
| GET    | /reports/cash-flow/pdf?fy=         | Cash Flow PDF download            |

### Data Improvements for Report Accuracy

The current reports are derived entirely from bank transaction imports and their category classifications. To improve accuracy beyond bank-level data, the following additional data sources could be integrated in future:

| Data Source | Reports Affected | Current Limitation |
|-------------|-----------------|-------------------|
| **Cash in hand** | Balance Sheet, Cash Flow | Only bank balances tracked; physical cash not captured |
| **Accounts receivable / payable** | Balance Sheet, Cash Flow | Outstanding invoices not tracked (no AR/AP module) |
| **Fixed asset register** | Balance Sheet, P&L (Depreciation) | Asset purchases via bank are categorized but no depreciation schedule |
| **Inventory valuation** | Balance Sheet | Inventory transactions via bank visible but stock value not tracked |
| **Loans breakdown** | Balance Sheet | Loan amounts visible as categories but no principal vs interest split |
| **Accrual adjustments** | P&L, Cash Flow | Reports are cash-basis (bank movements). Accrual adjustments (prepaid, outstanding) not supported |
| **Inter-bank transfers** | Cash Flow | Transfers are excluded from reports, which is correct, but misclassification would skew cash flow |

## Bank Accounts

**URL**: `/banks/accounts`
**Purpose**: Manage bank accounts belonging to the organisation. Activate / deactivate, add, delete. Transactions are managed separately at `/banks/transactions`.

### Fields

| Field          | Required | Notes                                   |
|----------------|----------|-----------------------------------------|
| bank_name      | yes      | Text, e.g. "HDFC Bank"                 |
| account_name   | yes      | Name on the account (payee)             |
| account_number | yes      | Full account number displayed           |
| ifsc_code      | yes      | IFSC code                               |
| branch_name    | no       | Optional branch                         |
| notes          | no       | Free text                               |
| is_active      | —        | Boolean, default True (toggle on/off)   |
| is_system      | —        | Boolean, default False, True for system accounts (cannot be deleted) |
| created_at     | —        | Auto-set on create                      |
| updated_at     | —        | Auto-set on every update                |

### UI Layout

- Page title: `Bank Accounts`
- Primary action: `+ Add Bank Account` button → HTMX loads a form card in-place (id: `#hx-account-form`).
- List: Bootstrap compact table (`table-sm table-hover align-middle`).
- Status column: `form-switch` checkbox posts via HTMX to `/banks/accounts/{id}/toggle`; response swaps the single row (`outerHTML`).
- Actions: Edit (HTMX form swap), Delete (security modal — type `DELETE` to confirm; blocked if account has transactions).
- Empty state: single card "No bank accounts yet. Add one to get started."
- Responses: HTMX requests return the `partials/bank_account_list.html` partial (swaps the `#hx-account-list` container). Add form is `partials/bank_account_form.html` (swaps `#hx-account-form`).

### Delete Protection

- A bank account cannot be deleted if it has associated transactions. The user must delete all transactions first.
- Delete uses a security modal requiring the user to type `DELETE` to confirm.
- `GET /banks/accounts/{id}/check-delete` returns `{"can_delete": bool, "txn_count": int, "message": str}`.
- `DELETE /banks/accounts/{id}` returns HTTP 409 if the account has transactions.

### Routes

| Method   | URL                                | Purpose                         |
|----------|------------------------------------|---------------------------------|
| GET      | /banks/accounts                    | Page                            |
| GET      | /banks/accounts/form               | Add form partial                |
| GET      | /banks/accounts/{id}/edit          | Edit form partial               |
| POST     | /banks/accounts                    | Create (HTMX)                   |
| PATCH    | /banks/accounts/{id}/toggle        | Toggle active (HTMX, swaps row) |
| DELETE   | /banks/accounts/{id}               | Delete (HTMX, blocked if has transactions) |
| GET      | /banks/accounts/{id}/check-delete  | Pre-delete check (JSON)         |

### System Account: Cash In Hand

A system-level bank account is automatically created during database initialization and cannot be deleted by users. This account is used to manage petty cash transactions.

| Attribute      | Value           |
|----------------|-----------------|
| bank_name      | Cash In Hand    |
| account_name   | Petty Cash      |
| is_system      | True            |

- **Creation**: Created automatically by `ensure_cash_in_hand()` in `app/services/bank_accounts.py` during `init_db()`. If the account already exists, no action is taken.
- **Delete Protection**: The account cannot be deleted. 
  - `DELETE /banks/accounts/{id}` returns HTTP 403 if the account is a system account.
  - The delete button is hidden in the UI for system accounts.
- **Transaction Support**: The system account fully supports import, export, edit, delete, and bulk operations just like any other bank account.
- **UI Behavior**: System accounts display a "System" badge instead of Delete/Edit buttons in the account list (`partials/bank_account_list.html`).

### Database

Table name: `bank_accounts`. Created by `init_db()`. Column `is_system` added via migration.

## Bank Transactions

**URL**: `/banks/transactions`
**Purpose**: Import, view, edit, delete, and export bank transactions for a selected account. Transactions are grouped by Indian financial year (April-March) and month.

### Fields

| Field        | Required | Notes                                          |
|--------------|----------|-------------------------------------------------|
| account_id   | yes      | FK → bank_accounts.id                          |
| txn_date     | yes      | ISO date (YYYY-MM-DD)                          |
| value_date   | yes      | ISO date (YYYY-MM-DD)                          |
| narration    | no       | Transaction description                        |
| reference    | no       | Cheque/reference number (shown below narration) |
| debit        | —        | Amount withdrawn (default 0)                   |
| credit       | —        | Amount deposited (default 0)                   |
| balance      | —        | Closing balance after transaction              |
| category_id  | —        | FK → transaction_categories.id (nullable)     |
| created_at   | —        | Auto-set on create                             |
| updated_at   | —        | Auto-set on every update                       |

### Import Formats (auto-detected via headers)

- **Dual-column** (e.g. HDFC): `Withdrawal Amt.` + `Deposit Amt.` columns
- **Single-column** (e.g. IDBI): `Amount (INR)` + `CR/DR` indicator column
- Supports CSV, XLS, XLSX
- **Kuku export files**: Can reimport exported CSV/XLSX files; parser auto-detects header rows and extracts Category column

### Categorisation

- Every imported transaction is auto-classified as `EXPENSE:Uncategorized Expense` (debit > 0) or `INCOME:Uncategorized Income` (credit > 0) by default.
- **Kuku export reimport**: When a Kuku export file is imported, categories from the file are recognized and mapped to the correct category IDs. Unmapped categories are mapped to Uncategorized and the user is informed which categories were not found.
- The `Category` column displays a unified **searchable select widget** for every transaction. Users type to filter (full-text search by category name and type), then click or use keyboard (Up/Down/Enter/Escape) to pick a category. No separate search input and select dropdown — it's one widget.
- When any category is changed, a global **Save / Cancel** bar appears above the table. Changed rows are highlighted with a yellow left border.
- **Save**: fires a PATCH per changed row, then reloads the table and removes the dirty row highlights.
- **Cancel**: restores every changed widget to its original value and hides the bar.
- If the user tries to navigate away with unsaved category changes, a browser `beforeunload` confirmation dialog fires.
- Unclassified transactions show the widget placeholder ("Search category…").

### Financial Year

- Follows Indian accounting standard: FY runs April to March. E.g., **FY 2025-26** = April 2025 – March 2026.
- Year dropdown shows `FY {start}-{end}` labels instead of calendar years.
- Month label combines month and calendar year, e.g., "Apr 2025", "Jan 2026".
- The filter URL uses the FY start year as the `fy` parameter (e.g., `fy=2025` for FY 2025-26).

### UI Layout

- Filter bar: account dropdown, FY dropdown, month dropdown (MM - MonthName Year) — all in a single row
- FY dropdown shows only financial years with uploaded transactions for the selected account
- Month dropdown shows only months with data for the selected FY
- When no transactions exist for an account, a "No transactions uploaded" message with an upload button is shown instead of filter dropdowns
- Summary cards: Total Debit, Total Credit, Net, Transaction Count
- Transaction table: compact Bootstrap `table-sm table-hover`
- Columns: Date | Narration (with `REF: reference` below in small muted text, only if reference exists) | Category (always-visible searchable `<select>`, grouped by Income / Expense / Asset / Liability / Equity) | Debit | Credit | Balance | Actions
- Narration column: multi-line, no truncation
- Reference: shown inline below narration as `(REF: <value>)` in `text-muted` small font. The `(REF: )` line is omitted entirely when the reference is empty.
- Actions per row: Edit (inline form via HTMX, textarea for narration), Delete (security modal — type `DELETE` to confirm)
- Import: file upload → preview (in modal dialog) → confirm → bulk insert
  - Preview shows Category column when categories are present in the file
  - Unmapped categories are shown with a warning alert and highlighted in the preview table
  - **Duplicate detection**: During preview, each incoming transaction is fingerprinted by `(account_id, txn_date, narration, reference, debit, credit)`. If a matching transaction already exists in the DB for the same account, it is flagged as a duplicate.
    - Preview shows a warning: "N duplicate transactions already exist and will be skipped."
    - Duplicate rows are marked with a `bi-arrow-repeat` icon in the preview table
    - On confirm, duplicate transactions are **skipped** by default (only new transactions are inserted)
    - The import summary (HX-Trigger data) includes `skipped` count alongside `count`
    - Post-import alert shows both counts: "X imported, Y skipped as duplicates."
  - `bank_transactions` table has a `txn_hash` column (SHA-256 of fingerprint fields) with a UNIQUE index to enforce dedup at DB level
- After successful import, filters and table auto-refresh to the imported FY/month
- Export: CSV, Excel (xlsx), PDF
  - All exports include: header (company name, bank name, period), transaction table, and summary footer
  - Header format: `{company_name}` → `{bank_name}, {account_last4}` → `{month} {year}`
  - Footer: totals row with debit/credit sums
  - PDF only: "Page X of Y" footer on each page
- Import workflow and transaction view workflow are isolated in a Bootstrap modal — the preview does not collide with the table area.

### Bulk Delete

- The **Delete Month** button appears in the header bar next to Import when an account is selected.
- Clicking it opens a modal with:
  - Warning header (red background)
  - Count of transactions to delete
  - Total debit and credit for the month
  - Text input requiring the user to type `DELETE` to confirm
  - Confirm button that stays disabled until the exact text matches
- This two-step confirmation (open modal + type DELETE) follows industry best practice for destructive bulk actions (cf. GitHub repository deletion, Stripe invoice deletion).
- Backend: `GET /transactions/bulk/summary` returns the summary; `DELETE /transactions/bulk/delete` performs the actual deletion.

### Run Rules

- The **Run Rules** button appears in the header bar next to Delete Month when an account is selected.
- Clicking it fires `POST /banks/transactions/rules/run` with `account_id`, `fy`, `month`.
- Backend evaluates all active classification rules in ascending priority order against every transaction in the selected month.
- **Account scoping**: Only rules where `account_id IS NULL` (all accounts) or `account_id` matches the selected account are evaluated.
- A rule applies only if its `applies_to` matches the transaction (`both` always matches, `debit` requires `debit > 0`, `credit` requires `credit > 0`).
- First matching rule wins; transaction category is updated if different.
- Response JSON: `{"updated": <count>}`.
- Frontend shows a success alert with the count and reloads the table.

### Routes

| Method | URL                                             | Purpose                              |
|--------|-------------------------------------------------|--------------------------------------|
| GET    | /banks/transactions                             | Page                                 |
| GET    | /banks/transactions/filters?account_id=&selected_fy=&selected_month= | FY/month dropdowns (HTMX)            |
| GET    | /banks/transactions/table?account_id=&fy=&month= | Transaction table (HTMX)            |
| GET    | /banks/transactions/import/form?account_id=     | Import file upload form (modal)      |
| POST   | /banks/transactions/import/preview              | Parse file, show preview (modal)     |
| POST   | /banks/transactions/import/confirm              | Bulk insert transactions             |
| GET    | /banks/transactions/{id}/edit                   | Inline edit form (HTMX)              |
| POST   | /banks/transactions/{id}/update                 | Update single transaction            |
| PATCH  | /banks/transactions/{id}/category               | Inline category save (returns 200)   |
| DELETE | /banks/transactions/{id}                        | Delete single transaction            |
| GET    | /banks/transactions/{id}/cancel                 | Cancel edit, show row (HTMX)         |
| GET    | /banks/transactions/bulk/summary                | Bulk delete summary (JSON)           |
| DELETE | /banks/transactions/bulk/delete                 | Bulk delete month's transactions     |
| POST   | /banks/transactions/rules/run                   | Apply classification rules (JSON)    |
| GET    | /banks/transactions/export/csv                  | Export as CSV                        |
| GET    | /banks/transactions/export/xlsx                 | Export as Excel                      |
| GET    | /banks/transactions/export/pdf                  | Export as PDF                        |

### Database

Table name: `bank_transactions`. Created by `init_db()` with FK to `bank_accounts`. `category_id` column is nullable; added via `ALTER TABLE` migration on startup. New transactions without category receive the auto-classified default on insert; existing unclassified transactions are retroactively classified on server start. System categories `Uncategorized Income` and `Uncategorized Expense` are seeded alongside the 39 default categories.

## Transaction Categories

**URL**: `/banks/categories`
**Purpose**: Manage transaction categories used to classify every bank transaction. Categories follow standard accounting classification (Income, Expense, Asset, Liability, Equity) per Indian Accounting Standards (ICAI) and international best practices (GAAP/IFRS). System categories are read-only; user categories can be added, edited, and deleted.

### Fields

| Field       | Required | Notes                                              |
|-------------|----------|----------------------------------------------------|
| name        | yes      | Category name, e.g. "Sales Revenue"                |
| type        | yes      | One of: Income, Expense, Asset, Liability, Equity  |
| description | no       | Brief description of the category                  |
| is_system   | —        | Boolean, 1 = system default (read-only), 0 = user  |
| created_at  | —        | Auto-set on create                                 |
| updated_at  | —        | Auto-set on every update                           |

### System Categories (43 defaults)

**Income (10):** Sales Revenue, Service Revenue, Interest Income, Rent Income, Commission Income, Dividend Income, Capital Gains, Shipping & Transport, Other Income, Uncategorized Income.
**Expense (19):** Cost of Goods Sold, Salaries & Wages, Payroll Taxes & Benefits, Rent & Lease, Utilities, Telephone & Internet, Advertising & Marketing, Insurance, Office Supplies, Professional Fees, Travel & Conveyance, Repairs & Maintenance, Bank Charges, Interest Paid, Depreciation, Tax Expense, Shipping & Transport, Miscellaneous Expense, Uncategorized Expense.
**Asset (5):** Cash & Bank, Accounts Receivable, Inventory, Fixed Assets, Investments.
**Liability (6):** Accounts Payable, Short-term Loans, Long-term Loans, Credit Card Payable, Tax Payable, Advances Received.
**Equity (3):** Owner Capital, Retained Earnings, Owner Drawings.
**Transfer (auto-managed):** Two transfer categories per bank account: `to {Bank Name} - {Account Name}` and `from {Bank Name} - {Account Name}`. These are system-managed and cannot be edited or deleted manually.

### UI Layout

- Page title: `Transaction Categories`
- Primary action: `+ Add Category` button → HTMX loads form card in-place (`#category-form-card`).
- List: Bootstrap compact table (`table-sm table-hover align-middle`).
- Type column: coloured badge (`bg-success-subtle` for Income, `bg-danger-subtle` for Expense, `bg-primary-subtle` for Asset, `bg-warning-subtle` for Liability, `bg-info-subtle` for Equity).
- System categories show a lock badge; no edit/delete actions.
- User categories show Edit (HTMX form swap) and Delete (security modal — type `DELETE` to confirm; blocked if category has transactions).
- Sort order: type → is_system DESC → name.
- Empty state: "No categories found."

### Routes

| Method | URL                                         | Purpose                          |
|--------|---------------------------------------------|----------------------------------|
| GET    | /banks/categories                           | Page                             |
| GET    | /banks/categories/form                      | Add form partial                 |
| GET    | /banks/categories/clear-form                | Clear form (HTMX)                |
| GET    | /banks/categories/{id}/edit                 | Edit form partial                |
| POST   | /banks/categories                           | Create (HTMX)                    |
| POST   | /banks/categories/{id}/update               | Update user category (HTMX)      |
| DELETE | /banks/categories/{id}                      | Delete user category (blocked if has transactions) |
| GET    | /banks/categories/{id}/check-delete         | Pre-delete check (JSON)          |

### Delete Protection

- A category cannot be deleted if it is used by any transaction. The user must update all transactions with a different category first.
- Delete uses a security modal requiring the user to type `DELETE` to confirm.
- `GET /banks/categories/{id}/check-delete` returns `{"can_delete": bool, "txn_count": int, "message": str}`.
- `DELETE /banks/categories/{id}` returns HTTP 409 if the category has transactions.

### Database

Table name: `transaction_categories`. Created by `init_db()`. System categories seeded on first `init_db()` run via `init_categories()`.

## Auto-Classification Rules

**URL**: `/banks/rules`
**Purpose**: Manage rules that automatically classify bank transactions based on narration text. Rules are evaluated in priority order when transactions are imported or when a user triggers re-classification.

### Fields

| Field          | Required | Notes                                                           |
|----------------|----------|-----------------------------------------------------------------|
| search_text    | yes      | Text to search for in the transaction narration                 |
| match_type     | yes      | One of: `contains` (case-insensitive substring), `equals` (case-insensitive exact match) |
| category_id    | yes      | FK → transaction_categories.id                                  |
| priority       | —        | Integer, lower = evaluated first (default 0)                    |
| applies_to     | —        | One of: `both` (default), `debit`, `credit`                     |
| account_id     | —        | FK → bank_accounts.id (nullable). NULL = all accounts, specific ID = only that account |
| is_active      | —        | Boolean, default True (toggle on/off)                           |
| created_at     | —        | Auto-set on create                                              |
| updated_at     | —        | Auto-set on every update                                        |

### Matching Logic

- Rules are evaluated in ascending `priority` order.
- Only active rules (`is_active = 1`) are considered.
- **Account scoping**: Only rules where `account_id IS NULL` (all accounts) or `account_id` matches the target account are evaluated.
- For each transaction, the first rule whose `search_text` matches the narration wins.
- `contains`: narration contains `search_text` (case-insensitive).
- `equals`: narration equals `search_text` (case-insensitive, trimmed).
- If no rule matches, the transaction keeps its existing category or defaults to uncategorized.

### UI Layout

- Page title: `Classification Rules`
- Primary action: `+ Add Rule` button → HTMX loads a form card in-place (`#rule-form-card`).
- List: Bootstrap compact table (`table-sm table-hover align-middle`).
- Columns: Priority | Search Text | Match Type | Category | Applies To | Account | Status | Actions
- Priority column: plain text, sorted ascending (lowest first). Edit priority via the Edit form.
- Account column: shows `Bank Name - Account Name` badge for account-specific rules, or `All Accounts` badge (green) when the rule applies to all accounts.
- Status column: `form-switch` checkbox posts via HTMX to toggle active/inactive.
- Actions: Edit (HTMX form swap), Delete (security modal — type `DELETE` to confirm).
- Category column: shows `TYPE:CategoryName` with a coloured badge.
- Match type badge: `bg-primary-subtle` for contains, `bg-info-subtle` for equals.
- Form includes a **Bank Account** dropdown with all accounts (including system accounts like Cash In Hand). Empty selection = all accounts.
- Empty state: "No rules yet. Add one to get started."
- Responses: HTMX requests return the `partials/rule_list.html` partial (swaps the `#hx-rule-list` container). Add form is `partials/rule_form.html` (swaps `#rule-form-card`).

### Routes

| Method   | URL                                | Purpose                         |
|----------|------------------------------------|---------------------------------|
| GET      | /banks/rules                       | Page                            |
| GET      | /banks/rules/form                  | Add form partial                |
| GET      | /banks/rules/clear-form            | Clear form (HTMX)               |
| GET      | /banks/rules/{id}/edit             | Edit form partial               |
| POST     | /banks/rules                       | Create (HTMX)                   |
| POST     | /banks/rules/{id}/update           | Update rule (HTMX)              |
| PATCH    | /banks/rules/{id}/priority         | Update priority (HTMX)          |
| PATCH    | /banks/rules/{id}/toggle           | Toggle active (HTMX)            |
| DELETE   | /banks/rules/{id}                  | Delete rule (HTMX)              |

### Database

Table name: `classification_rules`. Created by `init_db()`. Column `account_id` (nullable FK → bank_accounts.id) added via migration; NULL means the rule applies to all accounts.

## Export Service

**Package**: `app/services/exports/`
**Purpose**: Modular, domain-based export system. Each business domain (transactions, reports, invoices, etc.) has its own exporter class with CSV, XLSX, and PDF renderers.

### Architecture

```
app/services/exports/
├── __init__.py          # Public API: BaseExporter, TransactionExporter
├── base.py              # BaseExporter ABC, shared helpers (company name, account label)
└── transactions.py      # TransactionExporter (CSV, XLSX, PDF)

app/templates/exports/
├── transactions/
│   └── pdf.html         # Jinja2 HTML template rendered by xhtml2pdf
├── reports/
│   ├── profit_loss/pdf.html
│   ├── balance_sheet/pdf.html
│   └── cash_flow/pdf.html
└── invoices/            # (future)
```

### BaseExporter

Abstract base class. Subclasses set `domain` (used for template lookup and filenames) and implement `render_csv()`, `render_xlsx()`, `render_pdf()`.

Shared helpers in `base.py`:
- `get_company_name()` — reads `COMPANY_NAME` from config (loaded from `.env`)
- `build_account_label(account, account_id)` — `"Bank Name - ****1234"`
- `build_month_label(calendar_year, month)` — `"Apr 2025"`

### TransactionExporter

Subclass of `BaseExporter`. Accepts `account`, `account_id`, `fy`, `calendar_year`, `month` at construction. Data (`transactions`, `summary`) passed to render methods.

- **CSV**: Header (company name, account label, month), column headers, data rows, blank line, totals row. UTF-8 with BOM.
- **XLSX**: Merged header cells (company name centered, bank name, month label), column headers (bold), data rows with number formatting (`#,##0.00`), totals row (bold).
- **PDF**: Jinja2 HTML template (`templates/exports/transactions/pdf.html`) rendered to PDF via xhtml2pdf. Includes header, styled transaction table with alternating rows, summary section, and page footer ("Page X of Y").

### Adding a New Domain

1. Create `app/services/exports/<domain>.py` with a class extending `BaseExporter`.
2. Set `domain = "<domain>"` on the class.
3. Implement `render_csv()`, `render_xlsx()`, `render_pdf()`.
4. Add templates under `app/templates/exports/<domain>/`.
5. Export the class from `app/services/exports/__init__.py`.
6. Wire up route handlers that instantiate the exporter and call render methods.

## Backup & Restore

**URL**: `/backup`
**Purpose**: Export and import a single JSON file containing bank accounts, user categories, and classification rules. Allows quick reconfiguration on a fresh database without manually re-entering data.

### Backup JSON Schema (v2)

Single JSON file (`kuku-backup.json`) with a two-section design: `metadata` (information about the backup itself) and `data` (the actual records). This separation makes the format easy to extend — adding a new data type is just a new key under `data`.

```json
{
  "version": 2,
  "metadata": {
    "created_at": "2026-06-29T12:00:00Z",
    "created_by": "Kuku",
    "app_version": "1.0",
    "stats": {
      "bank_accounts": 5,
      "categories": 10,
      "rules": 15
    }
  },
  "data": {
    "bank_accounts": [...],
    "categories": [...],
    "rules": [...]
  }
}
```

| Schema Key              | Type     | Purpose                                              |
|-------------------------|----------|------------------------------------------------------|
| version                 | int      | Format version. v1 (flat) and v2 (structured) supported. |
| metadata.created_at     | string   | ISO 8601 UTC timestamp of when the backup was created |
| metadata.created_by     | string   | App name that produced the backup                    |
| metadata.app_version    | string   | App version at time of export                        |
| metadata.stats          | object   | Record counts per section (for quick preview without parsing `data`) |
| data.bank_accounts      | array    | All non-system accounts (user-created)               |
| data.categories         | array    | All non-system categories (user-created)             |
| data.rules              | array    | All classification rules (with category name+type references instead of IDs) |

**Adding a new section**: To support backing up a new data type (e.g. users, settings), add a new key under `data`, update the exporter to include it, update the importer to handle it, and bump `version` if the schema changes.

### Smart Analyze Step (Preview Before Import)

Before importing, the backup file is analyzed against the current database. The analysis is shown as an interactive preview:

- **Section toggles**: User can enable/disable each section (accounts, categories, rules) before importing.
- **To Import**: Records that will be created (new records not already in the database).
- **Already Exists**: Records skipped because a matching record already exists.
- **Warnings**: Rules that reference categories not found in the current database. The analyzer suggests similar category names when possible.
- **Empty file detection**: If the backup has zero records, an error is shown instead of the preview.
- **All-already-exist detection**: If every record in the backup already exists, the user is informed that there is nothing to import.

### Import Behaviour

- **Two-step flow**: Upload → Analyze preview → Confirm Import. Prevents accidental imports.
- **Token-based session**: After analysis, a short-lived token is generated and stored server-side. The confirm step uses this token (no need to re-upload the file). Token is consumed after one use.
- **Non-destructive**: Existing records are never overwritten.
- **Deduplication**: Records are matched by natural keys:
  - Bank accounts: `bank_name + account_name + account_number`
  - Categories: `name + type`
  - Rules: `search_text + match_type + category_id + priority`
- **Selective import**: User can choose which sections to import via checkboxes in the preview.
- **Partial import**: If some records fail (e.g., constraint violation), others still import. Per-record errors are tracked and shown in the result.
- **Category remapping**: Rules reference categories by `name + type` instead of ID, so they resolve correctly on a different database.
- **Transfer categories**: When a bank account is imported, its `to`/`from` transfer categories are automatically created.
- **Backward compatibility**: v1 (flat format: `{"version": 1, "exported_at": ..., "bank_accounts": [...]}`) is parsed and imported the same way as v2.

### Import Result Summary

After import, a detailed summary is shown:
- Per-section table: Created / Skipped / Errors counts
- Error details: Per-record error messages for any records that failed to import
- Option to import another backup

### Routes

| Method | URL              | Purpose                                    |
|--------|------------------|--------------------------------------------|
| GET    | /backup          | Backup & Restore page                      |
| GET    | /backup/export   | Download backup JSON file                  |
| POST   | /backup/analyze  | Analyze backup file, return preview HTML (HTMX) |
| POST   | /backup/import   | Confirm import using token, return result HTML (HTMX) |

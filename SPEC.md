# SPEC.md

## Overview

`kuku` is "Kuku" — a desktop-web hybrid business application built with Python.

### Sidebar Navigation Groups

| Group   | Link         | URL                      |
|---------|--------------|--------------------------|
|         | Dashboard    | /                        |
| BANKS   | Manage       | /banks/manage            |
| BANKS   | Transaction  | /banks/transactions      |
| BANKS   | Categories   | /banks/categories        |
| REPORTS | Reports      | /reports                 |
| ADMIN   | Settings     | /settings                |

## Bank Accounts (Manage)

**URL**: `/banks/manage`
**Purpose**: Manage bank accounts belonging to the organisation. Activate / deactivate, add, delete. Transactions are managed separately at `/banks/transactions`.

### Fields

| Field          | Required | Notes                                   |
|----------------|----------|-----------------------------------------|
| bank_name      | yes      | Text, e.g. "HDFC Bank"                 |
| account_name   | yes      | Name on the account (payee)             |
| account_number | yes      | Masked in list: last 4 digits visible   |
| ifsc_code      | yes      | IFSC code                               |
| branch_name    | no       | Optional branch                         |
| notes          | no       | Free text                               |
| is_active      | —        | Boolean, default True (toggle on/off)   |
| created_at     | —        | Auto-set on create                      |
| updated_at     | —        | Auto-set on every update                |

### UI Layout

- Page title: `Bank Accounts`
- Primary action: `+ Add Bank Account` button → HTMX loads a form card in-place (id: `#hx-account-form`).
- List: Bootstrap compact table (`table-sm table-hover align-middle`).
- Status column: `form-switch` checkbox posts via HTMX to `/banks/accounts/{id}/toggle`; response swaps the single row (`outerHTML`).
- Actions: Edit (HTMX form swap), Delete (`hx-delete` with `hx-confirm`).
- Empty state: single card "No bank accounts yet. Add one to get started."
- Responses: HTMX requests return the `partials/bank_account_list.html` partial (swaps the `#hx-account-list` container). Add form is `partials/bank_account_form.html` (swaps `#hx-account-form`).

### Routes

| Method   | URL                                | Purpose                         |
|----------|------------------------------------|---------------------------------|
| GET      | /banks/manage                      | Page                            |
| GET      | /banks/accounts/form               | Add form partial                |
| GET      | /banks/accounts/{id}/edit          | Edit form partial               |
| POST     | /banks/accounts                    | Create (HTMX)                   |
| PATCH    | /banks/accounts/{id}/toggle        | Toggle active (HTMX, swaps row) |
| DELETE   | /banks/accounts/{id}               | Delete (HTMX)                   |

### Database

Table name: `bank_accounts`. Created by `init_db()`.

## Bank Transactions

**URL**: `/banks/transactions`
**Purpose**: Import, view, edit, delete, and export bank transactions for a selected account. Transactions are grouped by year and month.

### Fields

| Field      | Required | Notes                                    |
|------------|----------|------------------------------------------|
| account_id | yes      | FK → bank_accounts.id                    |
| txn_date   | yes      | ISO date (YYYY-MM-DD)                    |
| value_date | yes      | ISO date (YYYY-MM-DD)                    |
| narration  | no       | Transaction description                  |
| reference  | no       | Cheque/reference number                  |
| debit      | —        | Amount withdrawn (default 0)             |
| credit     | —        | Amount deposited (default 0)             |
| balance    | —        | Closing balance after transaction        |
| created_at | —        | Auto-set on create                       |
| updated_at | —        | Auto-set on every update                 |

### Import Formats (auto-detected via headers)

- **Dual-column** (e.g. HDFC): `Withdrawal Amt.` + `Deposit Amt.` columns
- **Single-column** (e.g. IDBI): `Amount (INR)` + `CR/DR` indicator column
- Supports CSV, XLS, XLSX

### UI Layout

- Filter bar: account dropdown, year dropdown, month dropdown (MM - MMM) — all in a single row
- Year dropdown shows only years with uploaded transactions for the selected account
- Month dropdown shows only months with data for the selected year
- When no transactions exist for an account, a "No transactions uploaded" message with an Upload button is shown instead of year/month dropdowns
- Summary cards: Total Debit, Total Credit, Net, Transaction Count
- Transaction table: compact Bootstrap `table-sm table-hover`
- Narration column: multi-line, no truncation
- Actions per row: Edit (inline form via HTMX, textarea for narration), Delete (with confirmation)
- Import: file upload → preview table → confirm → bulk insert
- After successful import, filters and table auto-refresh
- Export: CSV, Excel (xlsx), PDF

### Routes

| Method | URL                                             | Purpose                              |
|--------|-------------------------------------------------|--------------------------------------|
| GET    | /banks/transactions                             | Page                                 |
| GET    | /banks/transactions/filters?account_id=&selected_year= | Year/month dropdowns (HTMX)          |
| GET    | /banks/transactions/table?account_id=&year=&month= | Transaction table (HTMX)            |
| GET    | /banks/transactions/import/form?account_id=     | Import file upload form              |
| POST   | /banks/transactions/import/preview              | Parse file, show preview             |
| POST   | /banks/transactions/import/confirm              | Bulk insert transactions             |
| GET    | /banks/transactions/{id}/edit                   | Inline edit form (HTMX)              |
| POST   | /banks/transactions/{id}/update                 | Update single transaction            |
| DELETE | /banks/transactions/{id}                        | Delete single transaction            |
| GET    | /banks/transactions/{id}/cancel                 | Cancel edit, show row (HTMX)         |
| GET    | /banks/transactions/export/csv                  | Export as CSV                        |
| GET    | /banks/transactions/export/xlsx                 | Export as Excel                      |
| GET    | /banks/transactions/export/pdf                  | Export as PDF                        |

### Database

Table name: `bank_transactions`. Created by `init_db()` with FK to `bank_accounts`.

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

### System Categories (39 defaults)

**Income (8):** Sales Revenue, Service Revenue, Interest Income, Rent Income, Commission Income, Dividend Income, Capital Gains, Other Income.
**Expense (17):** Cost of Goods Sold, Salaries & Wages, Payroll Taxes & Benefits, Rent & Lease, Utilities, Telephone & Internet, Advertising & Marketing, Insurance, Office Supplies, Professional Fees, Travel & Conveyance, Repairs & Maintenance, Bank Charges, Interest Paid, Depreciation, Tax Expense, Miscellaneous Expense.
**Asset (5):** Cash & Bank, Accounts Receivable, Inventory, Fixed Assets, Investments.
**Liability (6):** Accounts Payable, Short-term Loans, Long-term Loans, Credit Card Payable, Tax Payable, Advances Received.
**Equity (3):** Owner Capital, Retained Earnings, Owner Drawings.

### UI Layout

- Page title: `Transaction Categories`
- Primary action: `+ Add Category` button → HTMX loads form card in-place (`#category-form-card`).
- List: Bootstrap compact table (`table-sm table-hover align-middle`).
- Type column: coloured badge (`bg-success-subtle` for Income, `bg-danger-subtle` for Expense, `bg-primary-subtle` for Asset, `bg-warning-subtle` for Liability, `bg-info-subtle` for Equity).
- System categories show a lock badge; no edit/delete actions.
- User categories show Edit (HTMX form swap) and Delete (`hx-delete` with `hx-confirm`).
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
| DELETE | /banks/categories/{id}                      | Delete user category (HTMX)      |

### Database

Table name: `transaction_categories`. Created by `init_db()`. System categories seeded on first `init_db()` run via `init_categories()`.

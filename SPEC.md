# SPEC.md

## Overview

`kuku` is "Kuku" — a desktop-web hybrid business application built with Python.

### Sidebar Navigation Groups

| Group   | Link         | URL                      |
|---------|--------------|--------------------------|
|         | Dashboard    | /                        |
| BANKS   | Manage       | /banks/manage            |
| BANKS   | Transaction  | /banks/transactions      |
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

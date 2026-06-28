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
| BANKS   | Rules        | /banks/rules             |
| REPORTS | Reports      | /reports                 |
| ADMIN   | Settings     | /settings                |

### Configuration

Settings are loaded from a `.env` file in the project root (see `.env.example` for reference). `app/config.py` uses `python-dotenv` to load environment variables at startup.

| Variable       | Required | Default | Notes                                  |
|----------------|----------|---------|----------------------------------------|
| COMPANY_NAME   | no       | "Kuku"  | Displayed in export headers and reports |

Additional settings will be added here as the application grows.

## Bank Accounts (Manage)

**URL**: `/banks/manage`
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

### Categorisation

- Every imported transaction is auto-classified as `EXPENSE:Uncategorized Expense` (debit > 0) or `INCOME:Uncategorized Income` (credit > 0) by default.
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
- Actions per row: Edit (inline form via HTMX, textarea for narration), Delete (with confirmation)
- Import: file upload → preview (in modal dialog) → confirm → bulk insert
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

### System Categories (39 defaults)

**Income (8):** Sales Revenue, Service Revenue, Interest Income, Rent Income, Commission Income, Dividend Income, Capital Gains, Other Income.
**Expense (17):** Cost of Goods Sold, Salaries & Wages, Payroll Taxes & Benefits, Rent & Lease, Utilities, Telephone & Internet, Advertising & Marketing, Insurance, Office Supplies, Professional Fees, Travel & Conveyance, Repairs & Maintenance, Bank Charges, Interest Paid, Depreciation, Tax Expense, Miscellaneous Expense.
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
| is_active      | —        | Boolean, default True (toggle on/off)                           |
| created_at     | —        | Auto-set on create                                              |
| updated_at     | —        | Auto-set on every update                                        |

### Matching Logic

- Rules are evaluated in ascending `priority` order.
- Only active rules (`is_active = 1`) are considered.
- For each transaction, the first rule whose `search_text` matches the narration wins.
- `contains`: narration contains `search_text` (case-insensitive).
- `equals`: narration equals `search_text` (case-insensitive, trimmed).
- If no rule matches, the transaction keeps its existing category or defaults to uncategorized.

### UI Layout

- Page title: `Classification Rules`
- Primary action: `+ Add Rule` button → HTMX loads a form card in-place (`#rule-form-card`).
- List: Bootstrap compact table (`table-sm table-hover align-middle`).
- Columns: Priority | Search Text | Match Type | Category | Status | Actions
- Priority column: plain text, sorted ascending (lowest first). Edit priority via the Edit form.
- Status column: `form-switch` checkbox posts via HTMX to toggle active/inactive.
- Actions: Edit (HTMX form swap), Delete (`hx-delete` with `hx-confirm`).
- Category column: shows `TYPE:CategoryName` with a coloured badge.
- Match type badge: `bg-primary-subtle` for contains, `bg-info-subtle` for equals.
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

Table name: `classification_rules`. Created by `init_db()`.

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
└── (future domains: reports/, invoices/, etc.)
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

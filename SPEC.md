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

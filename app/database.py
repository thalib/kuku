import aiosqlite
from app import config

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(config.DB_PATH)
        _db.row_factory = aiosqlite.Row
    return _db


async def init_db():
    db = await get_db()
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS bank_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_name TEXT NOT NULL,
            account_name TEXT NOT NULL,
            account_number TEXT NOT NULL,
            ifsc_code TEXT NOT NULL,
            branch_name TEXT,
            notes TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS bank_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            txn_date TEXT NOT NULL,
            value_date TEXT NOT NULL,
            narration TEXT,
            reference TEXT,
            debit REAL NOT NULL DEFAULT 0,
            credit REAL NOT NULL DEFAULT 0,
            balance REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (account_id) REFERENCES bank_accounts(id)
        )
    """)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_bank_txn_date ON bank_transactions(txn_date)")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS transaction_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('Income', 'Expense', 'Transfer', 'Asset', 'Liability', 'Equity')),
            description TEXT,
            is_system INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    # Migration: Update old databases that don't have 'Transfer' in the CHECK constraint
    try:
        # Test if 'Transfer' type is already allowed
        await db.execute(
            "INSERT INTO transaction_categories (name, type, is_system) VALUES ('_test_transfer', 'Transfer', 1)"
        )
        await db.execute("DELETE FROM transaction_categories WHERE name = '_test_transfer'")
    except aiosqlite.IntegrityError:
        # Old schema detected - recreate table with new constraint
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS transaction_categories_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('Income', 'Expense', 'Transfer', 'Asset', 'Liability', 'Equity')),
                description TEXT,
                is_system INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            INSERT INTO transaction_categories_new SELECT * FROM transaction_categories;
            DROP TABLE transaction_categories;
            ALTER TABLE transaction_categories_new RENAME TO transaction_categories;
        """)
    try:
        await db.execute("ALTER TABLE bank_transactions ADD COLUMN category_id INTEGER DEFAULT NULL")
    except aiosqlite.OperationalError:
        pass
    try:
        await db.execute("ALTER TABLE bank_transactions ADD COLUMN txn_hash TEXT DEFAULT ''")
    except aiosqlite.OperationalError:
        pass
    await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_txn_hash ON bank_transactions(account_id, txn_hash) WHERE txn_hash != ''")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS classification_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_text TEXT NOT NULL,
            match_type TEXT NOT NULL CHECK(match_type IN ('contains', 'equals')),
            category_id INTEGER NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (category_id) REFERENCES transaction_categories(id)
        )
    """)
    # Migration: ensure classification_rules has is_active column (old schema)
    try:
        await db.execute("SELECT is_active FROM classification_rules LIMIT 1")
    except aiosqlite.OperationalError:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS classification_rules_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_text TEXT NOT NULL,
                match_type TEXT NOT NULL CHECK(match_type IN ('contains', 'equals')),
                category_id INTEGER NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (category_id) REFERENCES transaction_categories(id)
            );
            INSERT INTO classification_rules_new SELECT id, search_text, match_type, category_id, priority, 1, created_at, updated_at FROM classification_rules;
            DROP TABLE classification_rules;
            ALTER TABLE classification_rules_new RENAME TO classification_rules;
        """)
    try:
        await db.execute("SELECT applies_to FROM classification_rules LIMIT 1")
    except aiosqlite.OperationalError:
        await db.execute("ALTER TABLE classification_rules ADD COLUMN applies_to TEXT NOT NULL DEFAULT 'both'")
    try:
        await db.execute("ALTER TABLE bank_accounts ADD COLUMN is_system INTEGER NOT NULL DEFAULT 0")
    except aiosqlite.OperationalError:
        pass
    from app.services.bank_accounts import ensure_cash_in_hand
    await ensure_cash_in_hand(db)
    from app.services.categories import init_categories
    await init_categories(db)
    from app.services.transactions import auto_classify_existing_transactions
    await auto_classify_existing_transactions(db)
    await db.commit()


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None

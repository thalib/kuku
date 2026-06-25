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
    await db.commit()


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None

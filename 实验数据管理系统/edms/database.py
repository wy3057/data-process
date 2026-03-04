from __future__ import annotations

import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "experiment_data.db") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.init_schema()

    def init_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(owner_id, name),
                FOREIGN KEY(owner_id) REFERENCES users(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS experiment_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                researcher TEXT NOT NULL,
                experiment_date TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(owner_id) REFERENCES users(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS experiment_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                data_name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                recorded_at TEXT NOT NULL,
                operator TEXT NOT NULL,
                record_id INTEGER,
                remarks TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(owner_id) REFERENCES users(id),
                FOREIGN KEY(category_id) REFERENCES categories(id),
                FOREIGN KEY(record_id) REFERENCES experiment_records(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS web_sessions (
                sid TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )

        self.conn.commit()

        self._migrate_legacy_schema()
        self._create_indexes()

    def _create_indexes(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_owner_id ON categories(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_owner_status ON experiment_records(owner_id, status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_owner_time ON experiment_data(owner_id, recorded_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_category_id ON experiment_data(category_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_web_sessions_expires_at ON web_sessions(expires_at)")
        self.conn.commit()

    def _has_column(self, table_name: str, column_name: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return any(r["name"] == column_name for r in cursor.fetchall())

    def _migrate_legacy_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_keys = OFF")

        if not self._has_column("categories", "owner_id"):
            cursor.execute(
                """
                CREATE TABLE categories_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(owner_id, name),
                    FOREIGN KEY(owner_id) REFERENCES users(id)
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO categories_new(id, owner_id, name, description, created_at)
                SELECT id, 1, name, description, created_at FROM categories
                """
            )
            cursor.execute("DROP TABLE categories")
            cursor.execute("ALTER TABLE categories_new RENAME TO categories")

        if not self._has_column("experiment_records", "owner_id"):
            cursor.execute(
                """
                CREATE TABLE experiment_records_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    researcher TEXT NOT NULL,
                    experiment_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(owner_id) REFERENCES users(id)
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO experiment_records_new(id, owner_id, title, researcher, experiment_date, status, notes, created_at)
                SELECT id, 1, title, researcher, experiment_date, status, notes, created_at
                FROM experiment_records
                """
            )
            cursor.execute("DROP TABLE experiment_records")
            cursor.execute("ALTER TABLE experiment_records_new RENAME TO experiment_records")

        if not self._has_column("experiment_data", "owner_id"):
            cursor.execute(
                """
                CREATE TABLE experiment_data_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER NOT NULL,
                    data_name TEXT NOT NULL,
                    category_id INTEGER NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    recorded_at TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    record_id INTEGER,
                    remarks TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(owner_id) REFERENCES users(id),
                    FOREIGN KEY(category_id) REFERENCES categories(id),
                    FOREIGN KEY(record_id) REFERENCES experiment_records(id)
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO experiment_data_new(
                    id, owner_id, data_name, category_id, value, unit, recorded_at, operator, record_id, remarks, created_at
                )
                SELECT id, 1, data_name, category_id, value, unit, recorded_at, operator, record_id, remarks, created_at
                FROM experiment_data
                """
            )
            cursor.execute("DROP TABLE experiment_data")
            cursor.execute("ALTER TABLE experiment_data_new RENAME TO experiment_data")

        self.conn.commit()
        cursor.execute("PRAGMA foreign_keys = ON")

    @staticmethod
    def now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def close(self) -> None:
        self.conn.close()

from __future__ import annotations

import sqlite3

from edms.database import Database


class CategoryService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add_category(self, name: str, description: str | None = None, owner_id: int = 1) -> int:
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT INTO categories(owner_id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (owner_id, name, description, self.db.now()),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def list_categories(self, owner_id: int | None = None) -> list[sqlite3.Row]:
        cursor = self.db.conn.cursor()
        if owner_id is None:
            cursor.execute("SELECT id, owner_id, name, description, created_at FROM categories ORDER BY id")
        else:
            cursor.execute(
                "SELECT id, owner_id, name, description, created_at FROM categories WHERE owner_id=? ORDER BY id",
                (owner_id,),
            )
        return cursor.fetchall()

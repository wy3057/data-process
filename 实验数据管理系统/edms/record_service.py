from __future__ import annotations

import sqlite3

from edms.database import Database


class RecordService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add_record(
        self,
        title: str,
        researcher: str,
        experiment_date: str,
        status: str,
        notes: str | None = None,
        owner_id: int = 1,
    ) -> int:
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO experiment_records(owner_id, title, researcher, experiment_date, status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (owner_id, title, researcher, experiment_date, status, notes, self.db.now()),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def list_records(self, status: str | None = None, owner_id: int | None = None) -> list[sqlite3.Row]:
        cursor = self.db.conn.cursor()
        sql = """
            SELECT id, owner_id, title, researcher, experiment_date, status, notes, created_at
            FROM experiment_records WHERE 1=1
        """
        params: list[object] = []
        if owner_id is not None:
            sql += " AND owner_id=?"
            params.append(owner_id)
        if status:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY id DESC"
        cursor.execute(sql, params)
        return cursor.fetchall()

    def update_record_status(self, record_id: int, status: str, owner_id: int | None = None) -> None:
        cursor = self.db.conn.cursor()
        if owner_id is None:
            cursor.execute("UPDATE experiment_records SET status=? WHERE id=?", (status, record_id))
        else:
            cursor.execute("UPDATE experiment_records SET status=? WHERE id=? AND owner_id=?", (status, record_id, owner_id))
        if cursor.rowcount == 0:
            raise ValueError(f"实验记录ID {record_id} 不存在")
        self.db.conn.commit()

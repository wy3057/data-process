from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from edms.database import Database


class DataService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add_data(
        self,
        data_name: str,
        category_id: int,
        value: float,
        unit: str,
        recorded_at: str,
        operator: str,
        record_id: int | None = None,
        remarks: str | None = None,
        owner_id: int = 1,
    ) -> int:
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id FROM categories WHERE id=? AND owner_id=?", (category_id, owner_id))
        if not cursor.fetchone():
            raise ValueError(f"分类ID {category_id} 不存在或不属于当前用户")

        if record_id is not None:
            cursor.execute("SELECT id FROM experiment_records WHERE id=? AND owner_id=?", (record_id, owner_id))
            if not cursor.fetchone():
                raise ValueError(f"实验记录ID {record_id} 不存在或不属于当前用户")

        cursor.execute(
            """
            INSERT INTO experiment_data(
                owner_id, data_name, category_id, value, unit, recorded_at, operator, record_id, remarks, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                owner_id,
                data_name,
                category_id,
                value,
                unit,
                recorded_at,
                operator,
                record_id,
                remarks,
                self.db.now(),
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def query_data(
        self,
        category_id: int | None = None,
        keyword: str | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
        owner_id: int | None = None,
    ) -> list[sqlite3.Row]:
        sql = """
            SELECT d.id, d.owner_id, d.data_name, c.name AS category_name, d.value, d.unit,
                   d.recorded_at, d.operator, d.record_id, d.remarks
            FROM experiment_data d
            JOIN categories c ON d.category_id = c.id
            WHERE 1=1
        """
        params: list[Any] = []
        if owner_id is not None:
            sql += " AND d.owner_id = ?"
            params.append(owner_id)
        if category_id is not None:
            sql += " AND d.category_id = ?"
            params.append(category_id)
        if keyword:
            sql += " AND (d.data_name LIKE ? OR d.operator LIKE ? OR d.remarks LIKE ?)"
            like = f"%{keyword}%"
            params.extend([like, like, like])
        if date_start:
            sql += " AND d.recorded_at >= ?"
            params.append(date_start)
        if date_end:
            sql += " AND d.recorded_at <= ?"
            params.append(date_end)

        sql += " ORDER BY d.recorded_at DESC"
        cursor = self.db.conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()

    def stats_by_category(self, owner_id: int | None = None) -> list[sqlite3.Row]:
        cursor = self.db.conn.cursor()
        sql = """
            SELECT c.id AS category_id,
                   c.name AS category_name,
                   COUNT(d.id) AS data_count,
                   ROUND(AVG(d.value), 4) AS avg_value,
                   MIN(d.value) AS min_value,
                   MAX(d.value) AS max_value
            FROM categories c
            LEFT JOIN experiment_data d ON c.id = d.category_id
            WHERE 1=1
        """
        params: list[Any] = []
        if owner_id is not None:
            sql += " AND c.owner_id=?"
            params.append(owner_id)
        sql += " GROUP BY c.id, c.name ORDER BY c.id"
        cursor.execute(sql, params)
        return cursor.fetchall()

    def export_data(self, fmt: str, output_path: str, owner_id: int | None = None) -> str:
        rows = self.query_data(owner_id=owner_id)
        data = [dict(r) for r in rows]
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if fmt == "json":
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        elif fmt == "csv":
            with out.open("w", newline="", encoding="utf-8") as f:
                if data:
                    writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
                    writer.writeheader()
                    writer.writerows(data)
                else:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            "id",
                            "owner_id",
                            "data_name",
                            "category_name",
                            "value",
                            "unit",
                            "recorded_at",
                            "operator",
                            "record_id",
                            "remarks",
                        ]
                    )
        else:
            raise ValueError("仅支持导出为 json 或 csv")
        return str(out)

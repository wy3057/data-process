from __future__ import annotations

import argparse
import sqlite3

from edms.app import ExperimentDataSystem
from edms.ui import run_ui
from edms.web_ui import run_web_ui


def print_rows(rows: list[sqlite3.Row]) -> None:
    if not rows:
        print("(无数据)")
        return
    for row in rows:
        print(dict(row))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="实验数据管理系统")
    parser.add_argument("--db", default="experiment_data.db", help="SQLite数据库文件路径")
    parser.add_argument("--owner-id", type=int, default=1, help="业务命令使用的用户ID（默认1）")

    sub = parser.add_subparsers(dest="command", required=True)

    u1 = sub.add_parser("add-user", help="新增用户")
    u1.add_argument("username")
    u1.add_argument("password")

    sub.add_parser("list-users", help="查看用户")

    c1 = sub.add_parser("add-category", help="新增数据分类")
    c1.add_argument("name")
    c1.add_argument("--description", default="")

    sub.add_parser("list-categories", help="查看分类")

    r1 = sub.add_parser("add-record", help="新增实验记录")
    r1.add_argument("title")
    r1.add_argument("researcher")
    r1.add_argument("experiment_date", help="例如 2026-01-01")
    r1.add_argument("status", help="例如 planning/running/done")
    r1.add_argument("--notes", default="")

    r2 = sub.add_parser("list-records", help="查看实验记录")
    r2.add_argument("--status", default="")

    r3 = sub.add_parser("update-record-status", help="更新实验记录状态")
    r3.add_argument("record_id", type=int)
    r3.add_argument("status")

    d1 = sub.add_parser("add-data", help="录入实验数据")
    d1.add_argument("data_name")
    d1.add_argument("category_id", type=int)
    d1.add_argument("value", type=float)
    d1.add_argument("unit")
    d1.add_argument("recorded_at", help="例如 2026-01-01 10:30:00")
    d1.add_argument("operator")
    d1.add_argument("--record-id", type=int, default=None)
    d1.add_argument("--remarks", default="")

    q1 = sub.add_parser("query-data", help="查询实验数据")
    q1.add_argument("--category-id", type=int)
    q1.add_argument("--keyword")
    q1.add_argument("--date-start")
    q1.add_argument("--date-end")

    sub.add_parser("stats", help="分类统计")

    e1 = sub.add_parser("export", help="导出数据")
    e1.add_argument("fmt", choices=["json", "csv"])
    e1.add_argument("output_path")

    sub.add_parser("ui", help="启动桌面图形界面(Tkinter)")

    w1 = sub.add_parser("web-ui", help="启动浏览器图形界面")
    w1.add_argument("--host", default="127.0.0.1")
    w1.add_argument("--port", type=int, default=8000)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ui":
        run_ui(args.db)
        return

    if args.command == "web-ui":
        run_web_ui(db_path=args.db, host=args.host, port=args.port)
        return

    system = ExperimentDataSystem(db_path=args.db)
    try:
        if args.command == "add-user":
            user_id = system.users.create_user(args.username, args.password)
            print(f"用户新增成功，ID={user_id}")

        elif args.command == "list-users":
            print_rows(system.users.list_users())

        elif args.command == "add-category":
            category_id = system.categories.add_category(args.name, args.description, owner_id=args.owner_id)
            print(f"分类新增成功，ID={category_id}")

        elif args.command == "list-categories":
            print_rows(system.categories.list_categories(owner_id=args.owner_id))

        elif args.command == "add-record":
            record_id = system.records.add_record(
                args.title, args.researcher, args.experiment_date, args.status, args.notes, owner_id=args.owner_id
            )
            print(f"实验记录新增成功，ID={record_id}")

        elif args.command == "list-records":
            print_rows(system.records.list_records(args.status or None, owner_id=args.owner_id))

        elif args.command == "update-record-status":
            system.records.update_record_status(args.record_id, args.status, owner_id=args.owner_id)
            print("实验记录状态更新成功")

        elif args.command == "add-data":
            data_id = system.data.add_data(
                args.data_name,
                args.category_id,
                args.value,
                args.unit,
                args.recorded_at,
                args.operator,
                args.record_id,
                args.remarks,
                owner_id=args.owner_id,
            )
            print(f"实验数据录入成功，ID={data_id}")

        elif args.command == "query-data":
            rows = system.data.query_data(
                category_id=args.category_id,
                keyword=args.keyword,
                date_start=args.date_start,
                date_end=args.date_end,
                owner_id=args.owner_id,
            )
            print_rows(rows)

        elif args.command == "stats":
            print_rows(system.data.stats_by_category(owner_id=args.owner_id))

        elif args.command == "export":
            out = system.data.export_data(args.fmt, args.output_path, owner_id=args.owner_id)
            print(f"导出完成：{out}")

    finally:
        system.close()

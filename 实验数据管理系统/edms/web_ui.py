from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from html import escape
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from edms.app import ExperimentDataSystem

logger = logging.getLogger(__name__)
SESSION_HOURS = 8


def _layout(title: str, body: str, username: str | None = None) -> str:
    auth = (
        f"<span>当前用户：{escape(username or '')}</span> <a href='/logout'>退出</a>"
        if username
        else "<a href='/login'>登录</a> <a href='/register'>注册</a>"
    )
    return f"""<!doctype html>
<html lang='zh-CN'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; background:#f7f7fb; }}
    .card {{ background:#fff; border-radius:8px; padding:16px; margin-bottom:16px; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
    h1,h2 {{ margin: 0 0 12px; }}
    input,select {{ padding:6px; margin:4px 6px 8px 0; min-width: 140px; }}
    button {{ padding:6px 12px; }}
    table {{ border-collapse: collapse; width: 100%; background:#fff; }}
    th,td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #fafafa; }}
    .msg {{ color: #0a7f28; margin-bottom: 8px; }}
    .err {{ color: #b00020; margin-bottom: 8px; }}
    nav a {{ margin-right:10px; }}
    .topbar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }}
  </style>
</head>
<body>
<div class='topbar'>
  <nav>
    <a href='/'>首页</a>
    <a href='/categories'>分类管理</a>
    <a href='/records'>实验记录</a>
    <a href='/data'>数据录入</a>
    <a href='/query'>查询统计</a>
    <a href='/export'>导出</a>
  </nav>
  <div>{auth}</div>
</div>
{body}
</body>
</html>"""


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _read_post(environ: dict) -> dict[str, str]:
    size = int(environ.get("CONTENT_LENGTH") or 0)
    data = environ["wsgi.input"].read(size).decode("utf-8") if size else ""
    parsed = parse_qs(data)
    return {k: v[0] for k, v in parsed.items()}


def _parse_cookies(environ: dict) -> dict[str, str]:
    raw = environ.get("HTTP_COOKIE", "")
    cookies: dict[str, str] = {}
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k] = v
    return cookies


def _redirect(start_response, location: str, headers: list[tuple[str, str]] | None = None):
    final_headers = [("Location", location)] + (headers or [])
    start_response("302 Found", final_headers)
    return [b""]


def _cookie_header(sid: str, secure: bool = False) -> str:
    parts = [f"sid={sid}", "Path=/", "HttpOnly", "SameSite=Lax"]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def _session_create(system: ExperimentDataSystem, user_id: int) -> str:
    sid = secrets.token_hex(24)
    now = datetime.now()
    expires = now + timedelta(hours=SESSION_HOURS)
    cur = system.db.conn.cursor()
    cur.execute(
        "INSERT INTO web_sessions(sid, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (sid, user_id, now.strftime("%Y-%m-%d %H:%M:%S"), expires.strftime("%Y-%m-%d %H:%M:%S")),
    )
    system.db.conn.commit()
    return sid


def _session_get(system: ExperimentDataSystem, sid: str):
    if not sid:
        return None
    cur = system.db.conn.cursor()
    cur.execute(
        """
        SELECT s.sid, s.user_id, s.expires_at, u.username
        FROM web_sessions s JOIN users u ON s.user_id = u.id
        WHERE s.sid=?
        """,
        (sid,),
    )
    row = cur.fetchone()
    if not row:
        return None
    if row["expires_at"] <= datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        _session_delete(system, sid)
        return None
    return row


def _session_delete(system: ExperimentDataSystem, sid: str) -> None:
    if not sid:
        return
    cur = system.db.conn.cursor()
    cur.execute("DELETE FROM web_sessions WHERE sid=?", (sid,))
    system.db.conn.commit()


def _session_cleanup(system: ExperimentDataSystem) -> None:
    cur = system.db.conn.cursor()
    cur.execute("DELETE FROM web_sessions WHERE expires_at <= ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    system.db.conn.commit()


def create_app(system: ExperimentDataSystem):
    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET").upper()
        secure_cookie = environ.get("wsgi.url_scheme") == "https"
        cookies = _parse_cookies(environ)
        session = _session_get(system, cookies.get("sid", ""))
        user_id = int(session["user_id"]) if session else None
        username = str(session["username"]) if session else None
        msg = ""

        try:
            _session_cleanup(system)

            if path == "/register":
                err = ""
                if method == "POST":
                    form = _read_post(environ)
                    try:
                        system.users.create_user(form.get("username", ""), form.get("password", ""))
                        return _redirect(start_response, "/login")
                    except Exception as exc:
                        err = str(exc)
                body = f"""
                <div class='card'>
                  <h2>用户注册</h2>
                  {f"<div class='err'>{escape(err)}</div>" if err else ""}
                  <form method='post'>
                    <input name='username' placeholder='用户名(字母数字下划线，3-32位)' required />
                    <input name='password' type='password' placeholder='密码(至少6位)' required />
                    <button type='submit'>注册</button>
                  </form>
                </div>
                """
                html = _layout("注册", body, username)
                start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                return [html.encode("utf-8")]

            if path == "/login":
                err = ""
                if method == "POST":
                    form = _read_post(environ)
                    user = system.users.authenticate(form.get("username", ""), form.get("password", ""))
                    if user:
                        sid = _session_create(system, int(user["id"]))
                        return _redirect(
                            start_response,
                            "/",
                            [("Set-Cookie", _cookie_header(sid, secure=secure_cookie))],
                        )
                    err = "用户名或密码错误"
                body = f"""
                <div class='card'>
                  <h2>用户登录</h2>
                  {f"<div class='err'>{escape(err)}</div>" if err else ""}
                  <form method='post'>
                    <input name='username' placeholder='用户名' required />
                    <input name='password' type='password' placeholder='密码' required />
                    <button type='submit'>登录</button>
                  </form>
                </div>
                """
                html = _layout("登录", body, username)
                start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                return [html.encode("utf-8")]

            if path == "/logout":
                sid = cookies.get("sid", "")
                _session_delete(system, sid)
                return _redirect(start_response, "/login", [("Set-Cookie", "sid=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax")])

            if user_id is None:
                return _redirect(start_response, "/login")

            if path == "/":
                body = f"""
                <div class='card'>
                  <h1>实验数据管理系统 Web UI</h1>
                  <p>欢迎你，{escape(username or '')}。当前为多用户模式，页面数据已按用户隔离。</p>
                </div>
                """
                html = _layout("首页", body, username)

            elif path == "/categories":
                if method == "POST":
                    form = _read_post(environ)
                    system.categories.add_category(form.get("name", ""), form.get("description", ""), owner_id=user_id)
                    msg = "分类新增成功"
                rows = system.categories.list_categories(owner_id=user_id)
                table = _table(
                    ["ID", "名称", "描述", "创建时间"],
                    [[r["id"], r["name"], r["description"] or "", r["created_at"]] for r in rows],
                )
                body = f"""
                <div class='card'>
                  <h2>分类管理</h2>
                  {f"<div class='msg'>{escape(msg)}</div>" if msg else ""}
                  <form method='post'>
                    <input name='name' placeholder='分类名称' required />
                    <input name='description' placeholder='描述' />
                    <button type='submit'>新增分类</button>
                  </form>
                </div>
                <div class='card'>{table}</div>
                """
                html = _layout("分类管理", body, username)

            elif path == "/records":
                if method == "POST":
                    form = _read_post(environ)
                    system.records.add_record(
                        form.get("title", ""),
                        form.get("researcher", ""),
                        form.get("experiment_date", ""),
                        form.get("status", "running"),
                        form.get("notes", ""),
                        owner_id=user_id,
                    )
                    msg = "实验记录新增成功"
                rows = system.records.list_records(owner_id=user_id)
                table = _table(
                    ["ID", "标题", "负责人", "实验日期", "状态", "备注"],
                    [[r["id"], r["title"], r["researcher"], r["experiment_date"], r["status"], r["notes"] or ""] for r in rows],
                )
                body = f"""
                <div class='card'>
                  <h2>实验记录管理</h2>
                  {f"<div class='msg'>{escape(msg)}</div>" if msg else ""}
                  <form method='post'>
                    <input name='title' placeholder='标题' required />
                    <input name='researcher' placeholder='负责人' required />
                    <input name='experiment_date' placeholder='实验日期 如 2026-01-10' required />
                    <input name='status' placeholder='状态 running' value='running' required />
                    <input name='notes' placeholder='备注' />
                    <button type='submit'>新增记录</button>
                  </form>
                </div>
                <div class='card'>{table}</div>
                """
                html = _layout("实验记录", body, username)

            elif path == "/data":
                if method == "POST":
                    form = _read_post(environ)
                    record_id_raw = form.get("record_id", "").strip()
                    system.data.add_data(
                        form.get("data_name", ""),
                        int(form.get("category_id", "0")),
                        float(form.get("value", "0")),
                        form.get("unit", ""),
                        form.get("recorded_at", ""),
                        form.get("operator", ""),
                        int(record_id_raw) if record_id_raw else None,
                        form.get("remarks", ""),
                        owner_id=user_id,
                    )
                    msg = "实验数据录入成功"
                body = f"""
                <div class='card'>
                  <h2>实验数据录入</h2>
                  {f"<div class='msg'>{escape(msg)}</div>" if msg else ""}
                  <form method='post'>
                    <input name='data_name' placeholder='数据名' required />
                    <input name='category_id' placeholder='分类ID' required />
                    <input name='value' placeholder='数值' required />
                    <input name='unit' placeholder='单位' required />
                    <input name='recorded_at' placeholder='记录时间 2026-01-10 09:00:00' required />
                    <input name='operator' placeholder='操作人' required />
                    <input name='record_id' placeholder='记录ID(可空)' />
                    <input name='remarks' placeholder='备注' />
                    <button type='submit'>录入数据</button>
                  </form>
                </div>
                """
                html = _layout("数据录入", body, username)

            elif path == "/query":
                params = parse_qs(environ.get("QUERY_STRING", ""))
                cat = params.get("category_id", [""])[0].strip()
                keyword = params.get("keyword", [""])[0].strip()
                date_start = params.get("date_start", [""])[0].strip()
                date_end = params.get("date_end", [""])[0].strip()
                mode = params.get("mode", ["query"])[0]

                if mode == "stats":
                    rows = system.data.stats_by_category(owner_id=user_id)
                    table = _table(
                        ["分类ID", "分类名", "数量", "均值", "最小值", "最大值"],
                        [[r["category_id"], r["category_name"], r["data_count"], r["avg_value"], r["min_value"], r["max_value"]] for r in rows],
                    )
                else:
                    rows = system.data.query_data(
                        category_id=int(cat) if cat else None,
                        keyword=keyword or None,
                        date_start=date_start or None,
                        date_end=date_end or None,
                        owner_id=user_id,
                    )
                    table = _table(
                        ["ID", "数据名", "分类", "值", "单位", "记录时间", "操作人", "记录ID", "备注"],
                        [
                            [
                                r["id"],
                                r["data_name"],
                                r["category_name"],
                                r["value"],
                                r["unit"],
                                r["recorded_at"],
                                r["operator"],
                                r["record_id"] or "",
                                r["remarks"] or "",
                            ]
                            for r in rows
                        ],
                    )

                body = f"""
                <div class='card'>
                  <h2>数据查询与统计</h2>
                  <form method='get'>
                    <input name='category_id' placeholder='分类ID' value='{escape(cat)}' />
                    <input name='keyword' placeholder='关键字' value='{escape(keyword)}' />
                    <input name='date_start' placeholder='开始时间' value='{escape(date_start)}' />
                    <input name='date_end' placeholder='结束时间' value='{escape(date_end)}' />
                    <button type='submit' name='mode' value='query'>查询</button>
                    <button type='submit' name='mode' value='stats'>分类统计</button>
                  </form>
                </div>
                <div class='card'>{table}</div>
                """
                html = _layout("查询统计", body, username)

            elif path == "/export":
                if method == "POST":
                    form = _read_post(environ)
                    output_path = form.get("output_path", "exports/all_data.json")
                    if output_path.startswith("/"):
                        raise ValueError("导出路径必须是项目相对路径")
                    out = system.data.export_data(form.get("fmt", "json"), output_path, owner_id=user_id)
                    msg = f"导出完成：{out}"
                body = f"""
                <div class='card'>
                  <h2>数据导出</h2>
                  {f"<div class='msg'>{escape(msg)}</div>" if msg else ""}
                  <form method='post'>
                    <select name='fmt'>
                      <option value='json'>json</option>
                      <option value='csv'>csv</option>
                    </select>
                    <input name='output_path' value='exports/all_data.json' style='min-width:300px' />
                    <button type='submit'>导出</button>
                  </form>
                </div>
                """
                html = _layout("数据导出", body, username)

            else:
                start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
                return [b"Not Found"]

            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [html.encode("utf-8")]

        except ValueError as exc:
            html = _layout("错误", f"<div class='card'><h2>操作失败</h2><div class='err'>{escape(str(exc))}</div></div>", username)
            start_response("400 Bad Request", [("Content-Type", "text/html; charset=utf-8")])
            return [html.encode("utf-8")]
        except Exception:
            logger.exception("Unhandled error in web UI")
            html = _layout("错误", "<div class='card'><h2>服务内部错误</h2><div class='err'>请稍后重试。</div></div>", username)
            start_response("500 Internal Server Error", [("Content-Type", "text/html; charset=utf-8")])
            return [html.encode("utf-8")]

    return app


def run_web_ui(db_path: str = "experiment_data.db", host: str = "127.0.0.1", port: int = 8000) -> None:
    system = ExperimentDataSystem(db_path)
    app = create_app(system)
    try:
        with make_server(host, port, app) as server:
            print(f"Web UI running at http://{host}:{port} (db={db_path})")
            server.serve_forever()
    finally:
        system.close()

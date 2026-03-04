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


NAV_ITEMS = [
    ("/", "首页"),
    ("/categories", "分类管理"),
    ("/records", "实验记录"),
    ("/data", "数据录入"),
    ("/query", "查询统计"),
    ("/export", "导出"),
]


def _layout(title: str, body: str, current_path: str, username: str | None = None) -> str:
    auth = (
        f"<span>当前用户：{escape(username or '')}</span> <a class='link' href='/logout'>退出</a>"
        if username
        else "<a class='link' href='/login'>登录</a> <a class='link' href='/register'>注册</a>"
    )
    nav_html = "".join(
        f"<a class='nav-item {'active' if current_path == path else ''}' href='{path}'>{name}</a>"
        for path, name in NAV_ITEMS
    )
    return f"""<!doctype html>
<html lang='zh-CN'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>{escape(title)}</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --border: #e5e7eb;
      --primary: #2563eb;
      --primary-soft: #dbeafe;
      --success: #16a34a;
      --danger: #dc2626;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, Arial, sans-serif; color: var(--text); background: var(--bg); }}
    .container {{ max-width: 1180px; margin: 0 auto; padding: 20px; }}
    .topbar {{
      position: sticky; top: 0; z-index: 10; margin-bottom: 16px;
      background: rgba(245,247,251,.95); backdrop-filter: blur(3px);
      border-bottom: 1px solid var(--border); padding: 10px 0;
    }}
    .topbar-inner {{ max-width: 1180px; margin: 0 auto; padding: 0 20px; display:flex; justify-content:space-between; align-items:center; gap:10px; }}
    nav {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .nav-item {{ text-decoration: none; color: var(--text); padding: 7px 12px; border-radius: 8px; border: 1px solid transparent; }}
    .nav-item:hover {{ background: #eef2ff; }}
    .nav-item.active {{ background: var(--primary-soft); color: var(--primary); border-color: #bfdbfe; font-weight: 600; }}
    .link {{ color: var(--primary); text-decoration: none; margin-left: 8px; }}

    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 16px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(17,24,39,.04); }}
    h1 {{ margin: 0 0 10px; font-size: 24px; }}
    h2 {{ margin: 0 0 12px; font-size: 20px; }}
    p {{ margin: 0; color: var(--muted); }}

    .grid-3 {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .stat {{ background: linear-gradient(180deg, #fff, #f9fafb); border: 1px solid var(--border); border-radius: 12px; padding: 12px; }}
    .stat .k {{ font-size: 12px; color: var(--muted); margin-bottom: 4px; }}
    .stat .v {{ font-size: 22px; font-weight: 700; color: var(--primary); }}

    .form-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; align-items: end; }}
    .form-field {{ display: flex; flex-direction: column; gap: 6px; }}
    label {{ font-size: 12px; color: var(--muted); }}
    input, select {{ width: 100%; padding: 9px 10px; border-radius: 9px; border: 1px solid #d1d5db; background: #fff; }}
    button {{ padding: 9px 12px; border-radius: 9px; border: 1px solid #1d4ed8; background: var(--primary); color: white; cursor: pointer; }}
    button.secondary {{ background: #fff; color: var(--text); border-color: #d1d5db; }}

    .msg {{ color: var(--success); background: #ecfdf3; border: 1px solid #bbf7d0; border-radius: 9px; padding: 8px 10px; margin-bottom: 10px; }}
    .err {{ color: var(--danger); background: #fef2f2; border: 1px solid #fecaca; border-radius: 9px; padding: 8px 10px; margin-bottom: 10px; }}

    .table-wrap {{ overflow: auto; border-radius: 10px; border: 1px solid var(--border); }}
    table {{ border-collapse: collapse; width: 100%; min-width: 760px; background: #fff; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 9px 10px; text-align: left; }}
    th {{ background: #f9fafb; font-weight: 600; }}

    @media (max-width: 900px) {{ .grid-3 {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<div class='topbar'>
  <div class='topbar-inner'>
    <nav>{nav_html}</nav>
    <div>{auth}</div>
  </div>
</div>
<div class='container'>
{body}
</div>
</body>
</html>"""


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in row) + "</tr>" for row in rows)
    return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


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
                <div class='card' style='max-width:520px;margin:40px auto;'>
                  <h2>用户注册</h2>
                  <p style='margin-bottom:12px;'>创建一个新账号后即可开始管理你的实验数据。</p>
                  {f"<div class='err'>{escape(err)}</div>" if err else ""}
                  <form method='post' class='form-grid'>
                    <div class='form-field'><label>用户名</label><input name='username' placeholder='字母数字下划线，3-32位' required /></div>
                    <div class='form-field'><label>密码</label><input name='password' type='password' placeholder='至少6位' required /></div>
                    <button type='submit'>注册</button>
                  </form>
                </div>
                """
                html = _layout("注册", body, path, username)
                start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                return [html.encode("utf-8")]

            if path == "/login":
                err = ""
                if method == "POST":
                    form = _read_post(environ)
                    user = system.users.authenticate(form.get("username", ""), form.get("password", ""))
                    if user:
                        sid = _session_create(system, int(user["id"]))
                        return _redirect(start_response, "/", [("Set-Cookie", _cookie_header(sid, secure=secure_cookie))])
                    err = "用户名或密码错误"
                body = f"""
                <div class='card' style='max-width:520px;margin:40px auto;'>
                  <h2>用户登录</h2>
                  <p style='margin-bottom:12px;'>登录后可访问分类、记录、数据录入与统计导出功能。</p>
                  {f"<div class='err'>{escape(err)}</div>" if err else ""}
                  <form method='post' class='form-grid'>
                    <div class='form-field'><label>用户名</label><input name='username' placeholder='请输入用户名' required /></div>
                    <div class='form-field'><label>密码</label><input name='password' type='password' placeholder='请输入密码' required /></div>
                    <button type='submit'>登录</button>
                  </form>
                </div>
                """
                html = _layout("登录", body, path, username)
                start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                return [html.encode("utf-8")]

            if path == "/logout":
                sid = cookies.get("sid", "")
                _session_delete(system, sid)
                return _redirect(start_response, "/login", [("Set-Cookie", "sid=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax")])

            if user_id is None:
                return _redirect(start_response, "/login")

            if path == "/":
                cat_count = len(system.categories.list_categories(owner_id=user_id))
                rec_count = len(system.records.list_records(owner_id=user_id))
                data_count = len(system.data.query_data(owner_id=user_id))
                body = f"""
                <div class='card'>
                  <h1>实验数据管理系统</h1>
                  <p>欢迎你，{escape(username or '')}。这里是你的个人实验数据工作台。</p>
                </div>
                <div class='grid-3'>
                  <div class='stat'><div class='k'>分类总数</div><div class='v'>{cat_count}</div></div>
                  <div class='stat'><div class='k'>实验记录数</div><div class='v'>{rec_count}</div></div>
                  <div class='stat'><div class='k'>数据条目数</div><div class='v'>{data_count}</div></div>
                </div>
                """
                html = _layout("首页", body, path, username)

            elif path == "/categories":
                if method == "POST":
                    form = _read_post(environ)
                    system.categories.add_category(form.get("name", ""), form.get("description", ""), owner_id=user_id)
                    msg = "分类新增成功"
                rows = system.categories.list_categories(owner_id=user_id)
                table = _table(["ID", "名称", "描述", "创建时间"], [[r["id"], r["name"], r["description"] or "", r["created_at"]] for r in rows])
                body = f"""
                <div class='card'>
                  <h2>分类管理</h2>
                  {f"<div class='msg'>{escape(msg)}</div>" if msg else ""}
                  <form method='post' class='form-grid'>
                    <div class='form-field'><label>分类名称</label><input name='name' placeholder='例如：化学实验' required /></div>
                    <div class='form-field'><label>描述</label><input name='description' placeholder='分类说明（可选）' /></div>
                    <button type='submit'>新增分类</button>
                  </form>
                </div>
                <div class='card'>{table}</div>
                """
                html = _layout("分类管理", body, path, username)

            elif path == "/records":
                if method == "POST":
                    form = _read_post(environ)
                    system.records.add_record(form.get("title", ""), form.get("researcher", ""), form.get("experiment_date", ""), form.get("status", "running"), form.get("notes", ""), owner_id=user_id)
                    msg = "实验记录新增成功"
                rows = system.records.list_records(owner_id=user_id)
                table = _table(["ID", "标题", "负责人", "实验日期", "状态", "备注"], [[r["id"], r["title"], r["researcher"], r["experiment_date"], r["status"], r["notes"] or ""] for r in rows])
                body = f"""
                <div class='card'>
                  <h2>实验记录管理</h2>
                  {f"<div class='msg'>{escape(msg)}</div>" if msg else ""}
                  <form method='post' class='form-grid'>
                    <div class='form-field'><label>标题</label><input name='title' required /></div>
                    <div class='form-field'><label>负责人</label><input name='researcher' required /></div>
                    <div class='form-field'><label>实验日期</label><input name='experiment_date' placeholder='2026-01-10' required /></div>
                    <div class='form-field'><label>状态</label><input name='status' value='running' required /></div>
                    <div class='form-field'><label>备注</label><input name='notes' /></div>
                    <button type='submit'>新增记录</button>
                  </form>
                </div>
                <div class='card'>{table}</div>
                """
                html = _layout("实验记录", body, path, username)

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
                  <form method='post' class='form-grid'>
                    <div class='form-field'><label>数据名</label><input name='data_name' required /></div>
                    <div class='form-field'><label>分类ID</label><input name='category_id' required /></div>
                    <div class='form-field'><label>数值</label><input name='value' required /></div>
                    <div class='form-field'><label>单位</label><input name='unit' required /></div>
                    <div class='form-field'><label>记录时间</label><input name='recorded_at' placeholder='2026-01-10 09:00:00' required /></div>
                    <div class='form-field'><label>操作人</label><input name='operator' required /></div>
                    <div class='form-field'><label>记录ID</label><input name='record_id' placeholder='可空' /></div>
                    <div class='form-field'><label>备注</label><input name='remarks' /></div>
                    <button type='submit'>录入数据</button>
                  </form>
                </div>
                """
                html = _layout("数据录入", body, path, username)

            elif path == "/query":
                params = parse_qs(environ.get("QUERY_STRING", ""))
                cat = params.get("category_id", [""])[0].strip()
                keyword = params.get("keyword", [""])[0].strip()
                date_start = params.get("date_start", [""])[0].strip()
                date_end = params.get("date_end", [""])[0].strip()
                mode = params.get("mode", ["query"])[0]

                if mode == "stats":
                    rows = system.data.stats_by_category(owner_id=user_id)
                    table = _table(["分类ID", "分类名", "数量", "均值", "最小值", "最大值"], [[r["category_id"], r["category_name"], r["data_count"], r["avg_value"], r["min_value"], r["max_value"]] for r in rows])
                else:
                    rows = system.data.query_data(category_id=int(cat) if cat else None, keyword=keyword or None, date_start=date_start or None, date_end=date_end or None, owner_id=user_id)
                    table = _table(["ID", "数据名", "分类", "值", "单位", "记录时间", "操作人", "记录ID", "备注"], [[r["id"], r["data_name"], r["category_name"], r["value"], r["unit"], r["recorded_at"], r["operator"], r["record_id"] or "", r["remarks"] or ""] for r in rows])

                body = f"""
                <div class='card'>
                  <h2>数据查询与统计</h2>
                  <form method='get' class='form-grid'>
                    <div class='form-field'><label>分类ID</label><input name='category_id' value='{escape(cat)}' /></div>
                    <div class='form-field'><label>关键字</label><input name='keyword' value='{escape(keyword)}' /></div>
                    <div class='form-field'><label>开始时间</label><input name='date_start' value='{escape(date_start)}' /></div>
                    <div class='form-field'><label>结束时间</label><input name='date_end' value='{escape(date_end)}' /></div>
                    <button type='submit' name='mode' value='query'>查询</button>
                    <button class='secondary' type='submit' name='mode' value='stats'>分类统计</button>
                  </form>
                </div>
                <div class='card'>{table}</div>
                """
                html = _layout("查询统计", body, path, username)

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
                  <form method='post' class='form-grid'>
                    <div class='form-field'><label>格式</label><select name='fmt'><option value='json'>json</option><option value='csv'>csv</option></select></div>
                    <div class='form-field'><label>路径</label><input name='output_path' value='exports/all_data.json' /></div>
                    <button type='submit'>导出</button>
                  </form>
                </div>
                """
                html = _layout("数据导出", body, path, username)

            else:
                start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
                return [b"Not Found"]

            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [html.encode("utf-8")]

        except ValueError as exc:
            html = _layout("错误", f"<div class='card'><h2>操作失败</h2><div class='err'>{escape(str(exc))}</div></div>", path, username)
            start_response("400 Bad Request", [("Content-Type", "text/html; charset=utf-8")])
            return [html.encode("utf-8")]
        except Exception:
            logger.exception("Unhandled error in web UI")
            html = _layout("错误", "<div class='card'><h2>服务内部错误</h2><div class='err'>请稍后重试。</div></div>", path, username)
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

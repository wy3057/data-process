from app import create_app
from app.extensions import db


def make_client():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()

    return app.test_client()


def register_and_login(client, username: str):
    assert client.post("/auth/register", json={"username": username, "password": "123456"}).status_code == 201
    assert client.post("/auth/login", json={"username": username, "password": "123456"}).status_code == 200


def test_full_api_flow():
    client = make_client()
    register_and_login(client, "alice")

    r = client.post(
        "/plans/",
        json={"title": "计划A", "objective": "验证流程", "start_date": "2026-01-01"},
    )
    assert r.status_code == 201
    plan_id = r.get_json()["id"]

    r = client.post(
        "/tasks/",
        json={"name": "任务1", "plan_id": plan_id, "deadline": "2026-01-20"},
    )
    assert r.status_code == 201
    task_id = r.get_json()["data"]["id"]

    r = client.post(
        "/records/",
        json={"step_name": "样本准备", "details": "完成样本编号", "task_id": task_id},
    )
    assert r.status_code == 201

    r = client.post(
        "/progress/",
        json={"percent": 50, "summary": "完成一半", "task_id": task_id},
    )
    assert r.status_code == 201

    r = client.post(
        "/reports/",
        json={"title": "阶段报告", "conclusion": "结果正常", "task_id": task_id},
    )
    assert r.status_code == 201


def test_task_crud_endpoints():
    client = make_client()
    register_and_login(client, "task_user")

    plan_id = client.post("/plans/", json={"title": "P", "objective": "O"}).get_json()["id"]
    create_resp = client.post("/tasks/", json={"name": "T1", "plan_id": plan_id})
    assert create_resp.status_code == 201
    task_id = create_resp.get_json()["data"]["id"]

    detail_resp = client.get(f"/tasks/{task_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json()["ok"] is True
    assert detail_resp.get_json()["data"]["name"] == "T1"

    patch_resp = client.patch(f"/tasks/{task_id}", json={"status": "doing", "name": "T1-updated"})
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["data"]["status"] == "doing"

    delete_resp = client.delete(f"/tasks/{task_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.get_json()["ok"] is True


def test_api_authorization_and_validation():
    client = make_client()
    register_and_login(client, "user_a")
    plan_a = client.post("/plans/", json={"title": "A", "objective": "OA"}).get_json()["id"]
    task_a = client.post("/tasks/", json={"name": "TA", "plan_id": plan_a}).get_json()["data"]["id"]

    assert client.post("/plans/", json={"title": "X", "objective": "Y", "start_date": "bad-date"}).status_code == 400
    invalid = client.post("/progress/", json={"percent": "abc", "summary": "x", "task_id": task_a})
    assert invalid.status_code == 400

    assert client.post("/auth/logout").status_code == 200
    register_and_login(client, "user_b")
    assert client.post("/tasks/", json={"name": "TB", "plan_id": plan_a}).status_code == 403
    assert client.post("/records/", json={"step_name": "s", "details": "d", "task_id": task_a}).status_code == 403
    assert client.get(f"/tasks/{task_a}").status_code == 403


def test_ui_login_and_create_plan():
    client = make_client()

    register_page = client.post(
        "/register",
        data={"username": "bob", "password": "123456"},
        follow_redirects=True,
    )
    assert register_page.status_code == 200

    login_page = client.post(
        "/login",
        data={"username": "bob", "password": "123456"},
        follow_redirects=True,
    )
    assert login_page.status_code == 200
    assert "实验过程管理仪表盘" in login_page.get_data(as_text=True)

    plans_page = client.post(
        "/ui/plans",
        data={"title": "UI计划", "objective": "UI创建验证", "status": "active"},
        follow_redirects=True,
    )
    assert plans_page.status_code == 200
    body = plans_page.get_data(as_text=True)
    assert "计划已创建" in body
    assert "UI计划" in body

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ExperimentPlan, ExperimentTask
from app.modules.utils import (
    ValidationError,
    api_error,
    api_success,
    get_user_plan,
    get_user_task,
    parse_date,
    parse_int,
    serialize_task,
)

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.get("/")
@login_required
def list_tasks():
    tasks = (
        ExperimentTask.query.join(ExperimentPlan)
        .filter(ExperimentPlan.user_id == current_user.id)
        .all()
    )
    return api_success([serialize_task(t) for t in tasks], message="任务列表获取成功")


@tasks_bp.get("/<int:task_id>")
@login_required
def get_task(task_id: int):
    task = get_user_task(task_id)
    if not task:
        return api_error("任务不存在或无权限", code="FORBIDDEN", status=403)
    return api_success(serialize_task(task), message="任务详情获取成功")


@tasks_bp.post("/")
@login_required
def create_task():
    payload = request.get_json() or {}
    try:
        plan_id = parse_int(payload.get("plan_id"), "plan_id")
        task = ExperimentTask(
            name=payload.get("name", "").strip(),
            description=payload.get("description", "").strip(),
            assignee=payload.get("assignee", "").strip(),
            deadline=parse_date(payload.get("deadline")),
            status=payload.get("status", "pending"),
            plan_id=plan_id,
        )
    except ValidationError as exc:
        return api_error(str(exc), code="VALIDATION_ERROR", status=400)

    if not task.name:
        return api_error("name 不能为空", code="VALIDATION_ERROR", status=400)

    if not get_user_plan(plan_id):
        return api_error("计划不存在或无权限", code="FORBIDDEN", status=403)

    db.session.add(task)
    db.session.commit()
    return api_success({"id": task.id}, message="任务创建成功", status=201)


@tasks_bp.patch("/<int:task_id>")
@login_required
def update_task(task_id: int):
    task = get_user_task(task_id)
    if not task:
        return api_error("任务不存在或无权限", code="FORBIDDEN", status=403)

    payload = request.get_json() or {}
    try:
        if "plan_id" in payload:
            plan_id = parse_int(payload.get("plan_id"), "plan_id")
            if not get_user_plan(plan_id):
                return api_error("计划不存在或无权限", code="FORBIDDEN", status=403)
            task.plan_id = plan_id

        if "deadline" in payload:
            task.deadline = parse_date(payload.get("deadline"))
    except ValidationError as exc:
        return api_error(str(exc), code="VALIDATION_ERROR", status=400)

    if "name" in payload:
        task.name = (payload.get("name") or "").strip()
    if "description" in payload:
        task.description = (payload.get("description") or "").strip()
    if "assignee" in payload:
        task.assignee = (payload.get("assignee") or "").strip()
    if "status" in payload:
        task.status = (payload.get("status") or "").strip() or task.status

    if not task.name:
        return api_error("name 不能为空", code="VALIDATION_ERROR", status=400)

    db.session.commit()
    return api_success(serialize_task(task), message="任务更新成功")


@tasks_bp.delete("/<int:task_id>")
@login_required
def delete_task(task_id: int):
    task = get_user_task(task_id)
    if not task:
        return api_error("任务不存在或无权限", code="FORBIDDEN", status=403)

    db.session.delete(task)
    db.session.commit()
    return api_success(message="任务删除成功")

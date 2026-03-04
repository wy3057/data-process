from __future__ import annotations

from datetime import datetime

from flask import jsonify
from flask_login import current_user

from app.models import ExperimentPlan, ExperimentTask


class ValidationError(ValueError):
    pass


def api_success(data=None, message: str = "ok", status: int = 200):
    payload = {"ok": True, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def api_error(message: str, code: str = "BAD_REQUEST", status: int = 400, details=None):
    payload = {"ok": False, "error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return jsonify(payload), status


def parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError("日期格式必须为 YYYY-MM-DD") from exc


def parse_int(value, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} 必须为整数") from exc


def get_user_plan(plan_id: int) -> ExperimentPlan | None:
    return ExperimentPlan.query.filter_by(id=plan_id, user_id=current_user.id).first()


def get_user_task(task_id: int) -> ExperimentTask | None:
    return (
        ExperimentTask.query.join(ExperimentPlan)
        .filter(ExperimentTask.id == task_id, ExperimentPlan.user_id == current_user.id)
        .first()
    )


def serialize_task(task: ExperimentTask):
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "assignee": task.assignee,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "status": task.status,
        "plan_id": task.plan_id,
    }

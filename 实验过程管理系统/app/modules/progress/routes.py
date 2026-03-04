from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ExperimentPlan, ExperimentTask, ProgressEntry
from app.modules.utils import ValidationError, get_user_task, parse_int

progress_bp = Blueprint("progress", __name__)


@progress_bp.get("/")
@login_required
def list_progress():
    entries = (
        ProgressEntry.query.join(ExperimentTask)
        .join(ExperimentPlan)
        .filter(ExperimentPlan.user_id == current_user.id)
        .all()
    )
    return jsonify([
        {
            "id": e.id,
            "percent": e.percent,
            "summary": e.summary,
            "risk": e.risk,
            "task_id": e.task_id,
        }
        for e in entries
    ])


@progress_bp.post("/")
@login_required
def create_progress():
    payload = request.get_json() or {}
    try:
        percent = parse_int(payload.get("percent"), "percent")
        task_id = parse_int(payload.get("task_id"), "task_id")
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    entry = ProgressEntry(
        percent=percent,
        summary=payload.get("summary", "").strip(),
        risk=payload.get("risk", "").strip(),
        task_id=task_id,
    )
    if entry.percent < 0 or entry.percent > 100 or not entry.summary:
        return jsonify({"error": "percent 需在 0-100，summary 不能为空"}), 400

    if not get_user_task(task_id):
        return jsonify({"error": "任务不存在或无权限"}), 403

    db.session.add(entry)
    db.session.commit()
    return jsonify({"message": "进度记录创建成功", "id": entry.id}), 201

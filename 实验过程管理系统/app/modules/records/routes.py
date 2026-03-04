from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ExperimentPlan, ExperimentTask, ProcessRecord
from app.modules.utils import ValidationError, get_user_task, parse_int

records_bp = Blueprint("records", __name__)


@records_bp.get("/")
@login_required
def list_records():
    records = (
        ProcessRecord.query.join(ExperimentTask)
        .join(ExperimentPlan)
        .filter(ExperimentPlan.user_id == current_user.id)
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "step_name": r.step_name,
            "details": r.details,
            "operator": r.operator,
            "task_id": r.task_id,
            "record_time": r.record_time.isoformat(),
        }
        for r in records
    ])


@records_bp.post("/")
@login_required
def create_record():
    payload = request.get_json() or {}
    try:
        task_id = parse_int(payload.get("task_id"), "task_id")
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    record = ProcessRecord(
        step_name=payload.get("step_name", "").strip(),
        details=payload.get("details", "").strip(),
        operator=payload.get("operator", "").strip(),
        task_id=task_id,
    )
    if not record.step_name or not record.details:
        return jsonify({"error": "step_name、details 不能为空"}), 400

    if not get_user_task(task_id):
        return jsonify({"error": "任务不存在或无权限"}), 403

    db.session.add(record)
    db.session.commit()
    return jsonify({"message": "流程记录创建成功", "id": record.id}), 201

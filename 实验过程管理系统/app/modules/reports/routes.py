from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ExperimentPlan, ExperimentReport, ExperimentTask
from app.modules.utils import ValidationError, get_user_task, parse_int

reports_bp = Blueprint("reports", __name__)


@reports_bp.get("/")
@login_required
def list_reports():
    reports = (
        ExperimentReport.query.join(ExperimentTask)
        .join(ExperimentPlan)
        .filter(ExperimentPlan.user_id == current_user.id)
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "title": r.title,
            "conclusion": r.conclusion,
            "attachment": r.attachment,
            "task_id": r.task_id,
        }
        for r in reports
    ])


@reports_bp.post("/")
@login_required
def create_report():
    payload = request.get_json() or {}
    try:
        task_id = parse_int(payload.get("task_id"), "task_id")
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    report = ExperimentReport(
        title=payload.get("title", "").strip(),
        conclusion=payload.get("conclusion", "").strip(),
        attachment=payload.get("attachment", "").strip(),
        task_id=task_id,
    )
    if not report.title or not report.conclusion:
        return jsonify({"error": "title、conclusion 不能为空"}), 400

    if not get_user_task(task_id):
        return jsonify({"error": "任务不存在或无权限"}), 403

    db.session.add(report)
    db.session.commit()
    return jsonify({"message": "实验报告创建成功", "id": report.id}), 201

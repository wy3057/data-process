from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ExperimentPlan
from app.modules.utils import ValidationError, parse_date

plans_bp = Blueprint("plans", __name__)


@plans_bp.get("/")
@login_required
def list_plans():
    plans = ExperimentPlan.query.filter_by(user_id=current_user.id).all()
    return jsonify([
        {
            "id": p.id,
            "title": p.title,
            "objective": p.objective,
            "status": p.status,
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "end_date": p.end_date.isoformat() if p.end_date else None,
        }
        for p in plans
    ])


@plans_bp.post("/")
@login_required
def create_plan():
    payload = request.get_json() or {}
    try:
        plan = ExperimentPlan(
            title=payload.get("title", "").strip(),
            objective=payload.get("objective", "").strip(),
            start_date=parse_date(payload.get("start_date")),
            end_date=parse_date(payload.get("end_date")),
            status=payload.get("status", "draft"),
            user_id=current_user.id,
        )
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    if not plan.title or not plan.objective:
        return jsonify({"error": "title 和 objective 不能为空"}), 400

    db.session.add(plan)
    db.session.commit()
    return jsonify({"message": "计划创建成功", "id": plan.id}), 201

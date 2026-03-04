from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    plans = db.relationship("ExperimentPlan", backref="owner", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


class ExperimentPlan(TimestampMixin, db.Model):
    __tablename__ = "experiment_plans"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    objective = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(30), default="draft", nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    tasks = db.relationship("ExperimentTask", backref="plan", lazy=True, cascade="all, delete-orphan")


class ExperimentTask(TimestampMixin, db.Model):
    __tablename__ = "experiment_tasks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    assignee = db.Column(db.String(80))
    deadline = db.Column(db.Date)
    status = db.Column(db.String(30), default="pending", nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("experiment_plans.id"), nullable=False)

    records = db.relationship("ProcessRecord", backref="task", lazy=True, cascade="all, delete-orphan")
    progresses = db.relationship("ProgressEntry", backref="task", lazy=True, cascade="all, delete-orphan")
    reports = db.relationship("ExperimentReport", backref="task", lazy=True, cascade="all, delete-orphan")


class ProcessRecord(TimestampMixin, db.Model):
    __tablename__ = "process_records"

    id = db.Column(db.Integer, primary_key=True)
    step_name = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text, nullable=False)
    operator = db.Column(db.String(80))
    record_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey("experiment_tasks.id"), nullable=False)


class ProgressEntry(TimestampMixin, db.Model):
    __tablename__ = "progress_entries"

    id = db.Column(db.Integer, primary_key=True)
    percent = db.Column(db.Integer, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    risk = db.Column(db.Text)
    task_id = db.Column(db.Integer, db.ForeignKey("experiment_tasks.id"), nullable=False)


class ExperimentReport(TimestampMixin, db.Model):
    __tablename__ = "experiment_reports"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    conclusion = db.Column(db.Text, nullable=False)
    attachment = db.Column(db.String(255))
    task_id = db.Column(db.Integer, db.ForeignKey("experiment_tasks.id"), nullable=False)

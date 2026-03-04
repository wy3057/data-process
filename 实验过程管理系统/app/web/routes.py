from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import (
    ExperimentPlan,
    ExperimentReport,
    ExperimentTask,
    ProcessRecord,
    ProgressEntry,
    User,
)
from app.modules.utils import ValidationError, parse_date, parse_int

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("web.dashboard"))
    return redirect(url_for("web.login"))


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("web.dashboard"))
        flash("用户名或密码错误", "danger")
    return render_template("ui/login.html")


@web_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("用户名和密码不能为空", "danger")
        elif User.query.filter_by(username=username).first():
            flash("用户名已存在", "danger")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("注册成功，请登录", "success")
            return redirect(url_for("web.login"))
    return render_template("ui/register.html")


@web_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("web.login"))


@web_bp.get("/dashboard")
@login_required
def dashboard():
    stats = {
        "plans": ExperimentPlan.query.filter_by(user_id=current_user.id).count(),
        "tasks": ExperimentTask.query.join(ExperimentPlan).filter(ExperimentPlan.user_id == current_user.id).count(),
        "records": ProcessRecord.query.join(ExperimentTask).join(ExperimentPlan).filter(ExperimentPlan.user_id == current_user.id).count(),
        "progress": ProgressEntry.query.join(ExperimentTask).join(ExperimentPlan).filter(ExperimentPlan.user_id == current_user.id).count(),
        "reports": ExperimentReport.query.join(ExperimentTask).join(ExperimentPlan).filter(ExperimentPlan.user_id == current_user.id).count(),
    }
    return render_template("ui/dashboard.html", stats=stats)


@web_bp.route("/ui/plans", methods=["GET", "POST"])
@login_required
def plans_page():
    if request.method == "POST":
        try:
            plan = ExperimentPlan(
                title=request.form.get("title", "").strip(),
                objective=request.form.get("objective", "").strip(),
                start_date=parse_date(request.form.get("start_date")),
                end_date=parse_date(request.form.get("end_date")),
                status=request.form.get("status", "draft"),
                user_id=current_user.id,
            )
        except ValidationError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("web.plans_page"))

        if not plan.title or not plan.objective:
            flash("计划标题和目标不能为空", "danger")
        else:
            db.session.add(plan)
            db.session.commit()
            flash("计划已创建", "success")
            return redirect(url_for("web.plans_page"))

    plans = ExperimentPlan.query.filter_by(user_id=current_user.id).order_by(ExperimentPlan.id.desc()).all()
    return render_template("ui/plans.html", plans=plans)


@web_bp.route("/ui/tasks", methods=["GET", "POST"])
@login_required
def tasks_page():
    user_plans = ExperimentPlan.query.filter_by(user_id=current_user.id).all()
    plan_ids = {p.id for p in user_plans}

    if request.method == "POST":
        try:
            plan_id = parse_int(request.form.get("plan_id"), "plan_id")
            task = ExperimentTask(
                name=request.form.get("name", "").strip(),
                description=request.form.get("description", "").strip(),
                assignee=request.form.get("assignee", "").strip(),
                deadline=parse_date(request.form.get("deadline")),
                status=request.form.get("status", "pending"),
                plan_id=plan_id,
            )
        except ValidationError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("web.tasks_page"))

        if plan_id not in plan_ids:
            flash("计划不存在或无权限", "danger")
        elif not task.name:
            flash("任务名称不能为空", "danger")
        else:
            db.session.add(task)
            db.session.commit()
            flash("任务已创建", "success")
            return redirect(url_for("web.tasks_page"))

    tasks = ExperimentTask.query.join(ExperimentPlan).filter(ExperimentPlan.user_id == current_user.id).order_by(ExperimentTask.id.desc()).all()
    return render_template("ui/tasks.html", tasks=tasks, plans=user_plans)


@web_bp.route("/ui/records", methods=["GET", "POST"])
@login_required
def records_page():
    tasks = ExperimentTask.query.join(ExperimentPlan).filter(ExperimentPlan.user_id == current_user.id).all()
    task_ids = {t.id for t in tasks}

    if request.method == "POST":
        try:
            task_id = parse_int(request.form.get("task_id"), "task_id")
        except ValidationError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("web.records_page"))

        if task_id not in task_ids:
            flash("任务不存在或无权限", "danger")
        else:
            record = ProcessRecord(
                step_name=request.form.get("step_name", "").strip(),
                details=request.form.get("details", "").strip(),
                operator=request.form.get("operator", "").strip(),
                task_id=task_id,
            )
            if not record.step_name or not record.details:
                flash("步骤名称和详情不能为空", "danger")
            else:
                db.session.add(record)
                db.session.commit()
                flash("流程记录已创建", "success")
                return redirect(url_for("web.records_page"))

    records = ProcessRecord.query.join(ExperimentTask).join(ExperimentPlan).filter(ExperimentPlan.user_id == current_user.id).order_by(ProcessRecord.id.desc()).all()
    return render_template("ui/records.html", records=records, tasks=tasks)


@web_bp.route("/ui/progress", methods=["GET", "POST"])
@login_required
def progress_page():
    tasks = ExperimentTask.query.join(ExperimentPlan).filter(ExperimentPlan.user_id == current_user.id).all()
    task_ids = {t.id for t in tasks}

    if request.method == "POST":
        try:
            task_id = parse_int(request.form.get("task_id"), "task_id")
            percent = parse_int(request.form.get("percent"), "percent")
        except ValidationError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("web.progress_page"))

        if task_id not in task_ids:
            flash("任务不存在或无权限", "danger")
        elif percent < 0 or percent > 100:
            flash("进度必须在 0-100", "danger")
        else:
            entry = ProgressEntry(
                percent=percent,
                summary=request.form.get("summary", "").strip(),
                risk=request.form.get("risk", "").strip(),
                task_id=task_id,
            )
            if not entry.summary:
                flash("进度说明不能为空", "danger")
            else:
                db.session.add(entry)
                db.session.commit()
                flash("进度记录已创建", "success")
                return redirect(url_for("web.progress_page"))

    entries = ProgressEntry.query.join(ExperimentTask).join(ExperimentPlan).filter(ExperimentPlan.user_id == current_user.id).order_by(ProgressEntry.id.desc()).all()
    return render_template("ui/progress.html", entries=entries, tasks=tasks)


@web_bp.route("/ui/reports", methods=["GET", "POST"])
@login_required
def reports_page():
    tasks = ExperimentTask.query.join(ExperimentPlan).filter(ExperimentPlan.user_id == current_user.id).all()
    task_ids = {t.id for t in tasks}

    if request.method == "POST":
        try:
            task_id = parse_int(request.form.get("task_id"), "task_id")
        except ValidationError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("web.reports_page"))

        if task_id not in task_ids:
            flash("任务不存在或无权限", "danger")
        else:
            report = ExperimentReport(
                title=request.form.get("title", "").strip(),
                conclusion=request.form.get("conclusion", "").strip(),
                attachment=request.form.get("attachment", "").strip(),
                task_id=task_id,
            )
            if not report.title or not report.conclusion:
                flash("报告标题和结论不能为空", "danger")
            else:
                db.session.add(report)
                db.session.commit()
                flash("实验报告已创建", "success")
                return redirect(url_for("web.reports_page"))

    reports = ExperimentReport.query.join(ExperimentTask).join(ExperimentPlan).filter(ExperimentPlan.user_id == current_user.id).order_by(ExperimentReport.id.desc()).all()
    return render_template("ui/reports.html", reports=reports, tasks=tasks)

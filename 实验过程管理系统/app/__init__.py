import os

from flask import Flask

from app.auth.routes import auth_bp
from app.extensions import db, login_manager
from app.modules.plans.routes import plans_bp
from app.modules.progress.routes import progress_bp
from app.modules.records.routes import records_bp
from app.modules.reports.routes import reports_bp
from app.modules.tasks.routes import tasks_bp
from app.web.routes import web_bp


def create_app(test_config: dict | None = None):
    app = Flask(__name__, instance_relative_config=True)

    default_db = f"sqlite:///{os.path.join(app.instance_path, 'experiment.db')}"
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-key"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", default_db),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(plans_bp, url_prefix="/plans")
    app.register_blueprint(tasks_bp, url_prefix="/tasks")
    app.register_blueprint(records_bp, url_prefix="/records")
    app.register_blueprint(progress_bp, url_prefix="/progress")
    app.register_blueprint(reports_bp, url_prefix="/reports")

    with app.app_context():
        from app import models  # noqa: F401

        db.create_all()

    return app

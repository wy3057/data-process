from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/register")
def register():
    payload = request.get_json() or {}
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "username 和 password 不能为空"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "用户名已存在"}), 409

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "注册成功", "user_id": user.id}), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json() or {}
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "用户名或密码错误"}), 401

    login_user(user)
    return jsonify({"message": "登录成功", "user": user.username})


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "退出成功"})


@auth_bp.get("/me")
@login_required
def me():
    return jsonify({"id": current_user.id, "username": current_user.username})

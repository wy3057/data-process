from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3

from edms.database import Database


class UserService:
    USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")

    def __init__(self, db: Database) -> None:
        self.db = db

    @staticmethod
    def _hash_password(password: str, salt: str | None = None) -> str:
        real_salt = salt or os.urandom(16).hex()
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), real_salt.encode("utf-8"), 100_000).hex()
        return f"{real_salt}${digest}"

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        if "$" not in stored_hash:
            return False
        salt, _ = stored_hash.split("$", 1)
        candidate = UserService._hash_password(password, salt)
        return hmac.compare_digest(candidate, stored_hash)

    def create_user(self, username: str, password: str) -> int:
        username = username.strip()
        if not self.USERNAME_RE.match(username):
            raise ValueError("用户名需为3-32位，只能包含字母、数字、下划线")
        if len(password) < 6:
            raise ValueError("密码长度至少6位")

        cursor = self.db.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, self._hash_password(password), self.db.now()),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("用户名已存在") from exc
        self.db.conn.commit()
        return cursor.lastrowid

    def ensure_default_admin(self) -> None:
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username='admin'")
        if cursor.fetchone():
            return
        cursor.execute(
            "INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)",
            ("admin", self._hash_password("admin123"), self.db.now()),
        )
        self.db.conn.commit()

    def authenticate(self, username: str, password: str) -> sqlite3.Row | None:
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username=?", (username.strip(),))
        row = cursor.fetchone()
        if not row:
            return None
        if not self._verify_password(password, row["password_hash"]):
            return None
        return row

    def list_users(self) -> list[sqlite3.Row]:
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, username, created_at FROM users ORDER BY id")
        return cursor.fetchall()

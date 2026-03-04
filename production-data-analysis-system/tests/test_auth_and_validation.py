import unittest
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import crud, models
from app.database import Base
from app.main import validate_date_range
from app.schemas import UserRegister


class AuthAndValidationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_password_hash_and_verify(self):
        hashed = crud.hash_password("password123")
        self.assertTrue(hashed.startswith("pbkdf2_sha256$"))
        self.assertTrue(crud.verify_password("password123", hashed))
        self.assertFalse(crud.verify_password("wrong", hashed))

    def test_legacy_hash_upgrade_on_login(self):
        legacy_hash = __import__("hashlib").sha256("password123".encode("utf-8")).hexdigest()
        user = models.User(username="legacy_user", password_hash=legacy_hash)
        self.db.add(user)
        self.db.commit()

        verified = crud.verify_user(self.db, "legacy_user", "password123")
        self.assertIsNotNone(verified)
        refreshed = crud.get_user_by_username(self.db, "legacy_user")
        self.assertTrue(refreshed.password_hash.startswith("pbkdf2_sha256$"))

    def test_expired_session_will_be_cleaned(self):
        user = crud.create_user(self.db, UserRegister(username="u1", password="password123"))
        expired = models.UserSession(
            user_id=user.id,
            token="expired-token",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        self.db.add(expired)
        self.db.commit()

        current_user = crud.get_user_by_token(self.db, "expired-token")
        self.assertIsNone(current_user)
        self.assertIsNone(crud.get_session_by_token(self.db, "expired-token"))

    def test_validate_date_range(self):
        validate_date_range(date(2026, 1, 1), date(2026, 1, 31))
        with self.assertRaises(HTTPException):
            validate_date_range(date(2026, 2, 1), date(2026, 1, 1))


if __name__ == "__main__":
    unittest.main()

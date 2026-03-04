from __future__ import annotations

from edms.category_service import CategoryService
from edms.data_service import DataService
from edms.database import Database
from edms.record_service import RecordService
from edms.user_service import UserService


class ExperimentDataSystem:
    def __init__(self, db_path: str = "experiment_data.db") -> None:
        self.db = Database(db_path)
        self.users = UserService(self.db)
        self.users.ensure_default_admin()
        self.categories = CategoryService(self.db)
        self.records = RecordService(self.db)
        self.data = DataService(self.db)

    def close(self) -> None:
        self.db.close()

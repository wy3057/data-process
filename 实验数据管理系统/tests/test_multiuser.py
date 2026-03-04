from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from edms.app import ExperimentDataSystem


class TestMultiUserIsolation(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "t.db")
        self.system = ExperimentDataSystem(self.db_path)

    def tearDown(self) -> None:
        self.system.close()
        self.tmp.cleanup()

    def test_user_create_and_auth(self) -> None:
        uid = self.system.users.create_user("alice_1", "123456")
        self.assertGreater(uid, 1)
        row = self.system.users.authenticate("alice_1", "123456")
        self.assertIsNotNone(row)

    def test_data_isolation(self) -> None:
        user2 = self.system.users.create_user("bob_1", "123456")

        c1 = self.system.categories.add_category("cat_admin", "", owner_id=1)
        r1 = self.system.records.add_record("r1", "admin", "2026-01-01", "running", owner_id=1)
        self.system.data.add_data("d1", c1, 1.0, "u", "2026-01-01 10:00:00", "admin", r1, owner_id=1)

        c2 = self.system.categories.add_category("cat_bob", "", owner_id=user2)
        r2 = self.system.records.add_record("r2", "bob", "2026-01-01", "running", owner_id=user2)
        self.system.data.add_data("d2", c2, 2.0, "u", "2026-01-01 10:00:00", "bob", r2, owner_id=user2)

        admin_rows = self.system.data.query_data(owner_id=1)
        bob_rows = self.system.data.query_data(owner_id=user2)

        self.assertEqual(len(admin_rows), 1)
        self.assertEqual(admin_rows[0]["data_name"], "d1")
        self.assertEqual(len(bob_rows), 1)
        self.assertEqual(bob_rows[0]["data_name"], "d2")

    def test_cross_user_reference_rejected(self) -> None:
        user2 = self.system.users.create_user("charlie_1", "123456")
        c1 = self.system.categories.add_category("cat_admin", "", owner_id=1)
        with self.assertRaises(ValueError):
            self.system.data.add_data(
                "bad", c1, 3.0, "u", "2026-01-01 10:00:00", "charlie", owner_id=user2
            )


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, UTC
from pymongo import MongoClient
from app.models.ActivityRecord import ActivityRecord


# Before test should open the mangoDB service first
# Using the local mangoDB to do the test
class TestActivityRecordRealDB(unittest.TestCase):
    @classmethod
    #
    def setUpClass(self):
        self.client = MongoClient("mongodb://localhost:27017/")

        self.test_db = self.client["EDBA_TEST"]

        ActivityRecord.client = self.client
        ActivityRecord.db = self.test_db
        ActivityRecord.collection = self.test_db["ActivityRecord_UT"]

    def setUp(self):
        """Clear the collection before each test"""
        ActivityRecord.collection.delete_many({})

    def tearDown(self):
        """Clear the collection after each test"""
        ActivityRecord.collection.delete_many({})

    def test_add_record(self):
        test_user = "real_user"
        test_activity = "login"
        record = ActivityRecord(
            activityTime=datetime.now(UTC),
            userAccount=test_user,
            activityName=test_activity
        )

        record.addRecord()

        db_record = ActivityRecord.collection.find_one()
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record["userAccount"], test_user)
        self.assertEqual(db_record["activityName"], test_activity)

    def test_delete_record(self):
        test_user = "delete_test_user"
        test_activity = "delete_activity"
        record_test = ActivityRecord(
            activityTime=datetime.now(UTC),
            userAccount=test_user,
            activityName=test_activity
        )

        record_test.addRecord()
        deleted_count = record_test.deleteRecord()
        #print(deleted_count)
        self.assertEqual(deleted_count, 1)

    def test_display_records(self):
        # insert the test data
        test_data = [
            {
                "activityTime": datetime(2025, 4, 15, 9, 0, tzinfo=UTC),
                "userAccount": "display_user1",
                "activityName": "login"
            },
            {
                "activityTime": datetime(2025, 4, 15, 10, 0, tzinfo=UTC),
                "userAccount": "display_user2",
                "activityName": "logout"
            }
        ]
        ActivityRecord.collection.insert_many(test_data)

        # catch output
        import sys
        from io import StringIO

        original_stdout = sys.stdout
        sys.stdout = StringIO()

        ActivityRecord.displayRecord(self)

        output = sys.stdout.getvalue()
        sys.stdout = original_stdout
        # print output
        # print("\n=== Output ===")
        # print(output)

        self.assertIn("display_user1 - login", output)
        self.assertIn("display_user2 - logout", output)

        # Verify output order 
        self.assertTrue(output.index("display_user2") < output.index("display_user1"))

    def test_search_record_user_only(self):
        """Test only user account search"""
        test_data = [
            {
                "activityTime": datetime(2025, 4, 15, 10, 0, tzinfo=UTC),
                "userAccount": "userA",
                "activityName": "login"
            },
            {
                "activityTime": datetime(2025, 4, 15, 11, 0, tzinfo=UTC),
                "userAccount": "userA",
                "activityName": "logout"
            },
            {
                "activityTime": datetime(2025, 4, 15, 12, 0, tzinfo=UTC),
                "userAccount": "userB",
                "activityName": "login"
            }
        ]
        ActivityRecord.collection.insert_many(test_data)

        search_instance = ActivityRecord(
            activityTime=datetime.now(UTC),
            userAccount="userA",
            activityName="dummy"
        )
        results = search_instance.searchRecord(userAccount="userA")

        # print("\n=== Results ===")
        # for idx, record in enumerate(results, 1):
        #     print(f"Result{idx}:")
        #     print(f"  activityTime: {record['activityTime']}")
        #     print(f"  userAccount: {record['userAccount']}")
        #     print(f"  activityName: {record['activityName']}")

        self.assertEqual(len(results), 2)
        self.assertEqual({r["userAccount"] for r in results}, {"userA"})

    def test_search_record_activity_only(self):
        """Test only active name search"""
        test_data = [
            {
                "activityTime": datetime(2025, 4, 15, 9, 0, tzinfo=UTC),
                "userAccount": "userC",
                "activityName": "upload"
            },
            {
                "activityTime": datetime(2025, 4, 15, 10, 0, tzinfo=UTC),
                "userAccount": "userD",
                "activityName": "upload"
            },
            {
                "activityTime": datetime(2025, 4, 15, 11, 0, tzinfo=UTC),
                "userAccount": "userE",
                "activityName": "download"
            }
        ]
        ActivityRecord.collection.insert_many(test_data)

        search_instance = ActivityRecord(
            activityTime=datetime.now(UTC),
            userAccount="dummy",
            activityName="upload"
        )
        results = search_instance.searchRecord(activityName="upload")

        # print("\n=== Results ===")
        # for idx, record in enumerate(results, 1):
        #     print(f"Result{idx}:")
        #     print(f"  activityTime: {record['activityTime']}")
        #     print(f"  userAccount: {record['userAccount']}")
        #     print(f"  activityName: {record['activityName']}")

        self.assertEqual(len(results), 2)
        self.assertEqual({r["activityName"] for r in results}, {"upload"})

    def test_search_record_both_parameters(self):
        """Test the combined condition search"""
        test_data = [
            {
                "activityTime": datetime(2025, 4, 15, 8, 0, tzinfo=UTC),
                "userAccount": "userX",
                "activityName": "start"
            },
            {
                "activityTime": datetime(2025, 4, 15, 9, 0, tzinfo=UTC),
                "userAccount": "userX",
                "activityName": "stop"
            },
            {
                "activityTime": datetime(2025, 4, 15, 10, 0, tzinfo=UTC),
                "userAccount": "userY",
                "activityName": "start"
            }
        ]
        ActivityRecord.collection.insert_many(test_data)

        search_instance = ActivityRecord(
            activityTime=datetime.now(UTC),
            userAccount="userX",
            activityName="start"
        )
        results = search_instance.searchRecord(userAccount="userX", activityName="start")

        # print("\n=== Results ===")
        # for idx, record in enumerate(results, 1):
        #     print(f"Result{idx}:")
        #     print(f"  activityTime: {record['activityTime']}")
        #     print(f"  userAccount: {record['userAccount']}")
        #     print(f"  activityName: {record['activityName']}")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["activityName"], "start")

    def test_search_record_no_parameters(self):
        """Test parameterless search"""
        test_data = [
            {
                "activityTime": datetime(2025, 4, 15, 12, 0, tzinfo=UTC),
                "userAccount": "userM",
                "activityName": "create"
            },
            {
                "activityTime": datetime(2025, 4, 15, 13, 0, tzinfo=UTC),
                "userAccount": "userN",
                "activityName": "delete"
            }
        ]
        ActivityRecord.collection.insert_many(test_data)

        search_instance = ActivityRecord(
            activityTime=datetime.now(UTC),
            userAccount="dummy",
            activityName="dummy"
        )
        results = search_instance.searchRecord()

        # print("\n=== Results ===")
        # for idx, record in enumerate(results, 1):
        #     print(f"Result{idx}:")
        #     print(f"  activityTime: {record['activityTime']}")
        #     print(f"  userAccount: {record['userAccount']}")
        #     print(f"  activityName: {record['activityName']}")

        self.assertEqual(len(results), 2)
        self.assertEqual({r["userAccount"] for r in results}, {"userM", "userN"})
    # @classmethod
    # def tearDownClass(self):
    #     self.client.drop_database("tes")
    #     self.client.close()


if __name__ == '__main__':
    unittest.main()

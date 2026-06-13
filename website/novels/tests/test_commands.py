from django.test import TestCase
from django.core.management import call_command
from io import StringIO


class ManagementCommandTests(TestCase):
    def test_init_db_help(self):
        out = StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command("init_db", "--help", stdout=out)
        self.assertEqual(cm.exception.code, 0)

    def test_upsert_dataset_help(self):
        out = StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command("upsert_dataset", "--help", stdout=out)
        self.assertEqual(cm.exception.code, 0)

    def test_dump_dataset_help(self):
        out = StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command("dump_dataset", "--help", stdout=out)
        self.assertEqual(cm.exception.code, 0)

    def test_generate_static_help(self):
        out = StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command("generate_static", "--help", stdout=out)
        self.assertEqual(cm.exception.code, 0)

    def test_serve_static_help(self):
        out = StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command("serve_static", "--help", stdout=out)
        self.assertEqual(cm.exception.code, 0)

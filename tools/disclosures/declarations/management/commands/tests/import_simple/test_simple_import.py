from django.test import TestCase
from disclosures.declarations.management.commands.import_json import ImportJsonCommand


class SimpleImportTestCase(TestCase):
    def setUp(self):
        pass

    def test_simple_import(self):
        args = ["", "--dlrobot-human", "dlrobot_human.json"]
        importer = ImportJsonCommand(*args)
        importer.handle(*args)

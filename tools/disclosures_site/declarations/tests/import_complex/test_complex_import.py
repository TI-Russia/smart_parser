from django.test import TestCase
from declarations.management.commands.import_json import ImportJsonCommand
import os
import declarations.models as models


class ComplexImportTestCase(TestCase):
    def setUp(self):
        pass

    def test_complex_import(self):
        importer = ImportJsonCommand(None, None)
        os.chdir(os.path.dirname(__file__))
        importer.handle(None, dlrobot_human="dlrobot_human.json", smart_parser_human_json="human_jsons")
        self.assertEqual(models.Section.objects.count(), 3)
        self.assertEqual(models.RealEstate.objects.count(), 3)
        self.assertEqual(models.Income.objects.count(), 3)
        self.assertEqual(models.Income.objects.count(), 3)

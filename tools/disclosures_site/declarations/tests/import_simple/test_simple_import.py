from django.test import TestCase
from declarations.management.commands.import_json import ImportJsonCommand
import os
import declarations.models as models


class SimpleImportTestCase(TestCase):
    def setUp(self):
        pass

    def test_simple_import(self):
        importer = ImportJsonCommand(None, None)
        input_path = os.path.join(os.path.dirname(__file__), "dlrobot_human.json")
        importer.handle(None, dlrobot_human=input_path)
        self.assertEqual(models.Section.objects.count(), 1)
        self.assertEqual(models.RealEstate.objects.count(), 1)
        self.assertEqual(models.Income.objects.count(), 1)
        self.assertEqual(models.Income.objects.count(), 1)
        self.assertEqual(models.Income.objects.all()[:1].get().size, 1462642)

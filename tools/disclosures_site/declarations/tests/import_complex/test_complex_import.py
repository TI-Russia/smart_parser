from django.test import TestCase
from declarations.management.commands.import_json import ImportJsonCommand
import os
import declarations.models as models
from declarations.tests.test_smart_parser import SmartParserServerForTesting
from declarations.management.commands.permalinks import TPermaLinksDB


class ComplexImportTestCase(TestCase):
    def setUp(self):
        pass

    def test_complex_import(self):
        permalinks_path = os.path.join(os.path.dirname(__file__), "permalinks.dbm")
        p = TPermaLinksDB(permalinks_path)
        p.create_db()
        p.close()

        os.environ['SMART_PARSER_SERVER_ADDRESS'] = "localhost:8178"
        domains_folder = os.path.join(os.path.dirname(__file__), "domains")
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")

        importer = ImportJsonCommand(None, None)
        os.chdir(os.path.dirname(__file__))

        with SmartParserServerForTesting(sp_workdir, domains_folder):
            importer.handle(None, dlrobot_human="dlrobot_human.json", smart_parser_human_json="human_jsons",
                            permanent_links_db=permalinks_path)

        self.assertEqual(models.Section.objects.count(), 3)
        self.assertEqual(models.RealEstate.objects.count(), 3)
        self.assertEqual(models.Income.objects.count(), 3)
        self.assertEqual(models.Income.objects.count(), 3)

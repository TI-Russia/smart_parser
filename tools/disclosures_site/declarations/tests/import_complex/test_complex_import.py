from declarations.management.commands.import_json import ImportJsonCommand
from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
from declarations.management.commands.permalinks import TPermaLinksDB
from declarations.management.commands.create_permalink_storage import CreatePermalinksStorageCommand

from django.test import TestCase
import os
import declarations.models as models


class ComplexImportTestCase(TestCase):

    def test_complex_import(self):
        self.assertGreater(models.Office.objects.count(), 0)
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()

        permalinks_path = os.path.join(os.path.dirname(__file__), "permalinks.dbm")
        TPermaLinksDB(permalinks_path).create_and_save_empty_db()

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
        self.assertGreater(models.Office.objects.count(), 0)


        CreatePermalinksStorageCommand(None, None).handle(None, output_dbm_file=permalinks_path)
        permalinks_db = TPermaLinksDB(permalinks_path)
        permalinks_db.open_db_read_only()
        permalinks_db.create_sql_sequences()
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()
        with SmartParserServerForTesting(sp_workdir, domains_folder):
            importer.handle(None, dlrobot_human="dlrobot_human.json", smart_parser_human_json="human_jsons",
                            permanent_links_db=permalinks_path)

        #check that we reuse old section ids and source doc ids
        self.assertEqual(permalinks_db.get_new_max_id(models.Source_Document), None)
        self.assertEqual(permalinks_db.get_new_max_id(models.Section), None)
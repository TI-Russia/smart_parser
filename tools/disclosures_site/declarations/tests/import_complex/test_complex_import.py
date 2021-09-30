from declarations.management.commands.import_json import ImportJsonCommand
from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
from declarations.permalinks import TPermalinksManager
from declarations.management.commands.create_permalink_storage import CreatePermalinksStorageCommand
from common.logging_wrapper import setup_logging
from django.test import TestCase
import os
import declarations.models as models


class ComplexImportTestCase(TestCase):

    def test_complex_import(self):
        self.assertGreater(models.Office.objects.count(), 0)
        models.Income.objects.all().delete()
        models.RealEstate.objects.all().delete()
        models.Vehicle.objects.all().delete()
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()

        permalinks_folder = os.path.dirname(__file__)
        logger = setup_logging(log_file_name="test_complex_import.log")
        TPermalinksManager(logger, {'directory': permalinks_folder}).create_empty_dbs()

        doc_folder = os.path.join(os.path.dirname(__file__), "domains")
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")

        importer = ImportJsonCommand(None, None)
        os.chdir(os.path.dirname(__file__))

        with SmartParserServerForTesting(sp_workdir, doc_folder):
            importer.handle(None, dlrobot_human="dlrobot_human.json", smart_parser_human_json="human_jsons",
                            permalinks_folder=permalinks_folder)

        self.assertEqual(models.Section.objects.count(), 3)
        old_sections = [(s.id, s.person_name) for s in models.Section.objects.all()]

        self.assertEqual(models.RealEstate.objects.count(), 3)
        self.assertEqual(models.Income.objects.count(), 3)
        self.assertEqual(models.Income.objects.count(), 3)
        self.assertGreater(models.Office.objects.count(), 0)
        old_docs = [(d.id, d.sha256) for d in models.Source_Document.objects.all()]

        # import the same sections adn check that we reuse old section ids and source doc ids
        CreatePermalinksStorageCommand(None, None).handle(None, directory=permalinks_folder)
        permalinks_db = TPermalinksManager(logger, {'directory': permalinks_folder})
        permalinks_db.create_sql_sequences()
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()
        with SmartParserServerForTesting(sp_workdir, doc_folder):
            importer.handle(None, dlrobot_human="dlrobot_human.json", smart_parser_human_json="human_jsons",
                            permalinks_folder=permalinks_folder)

        new_docs = [(d.id, d.sha256) for d in models.Source_Document.objects.all()]
        self.assertListEqual(old_docs, new_docs)

        new_sections = [(s.id, s.person_name) for s in models.Section.objects.all()]
        self.assertListEqual(old_sections, new_sections)
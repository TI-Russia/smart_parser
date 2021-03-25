import declarations.models as models
from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
from declarations.permalinks import TPermaLinksSection, TPermaLinksSourceDocument
from declarations.management.commands.import_json import ImportJsonCommand
from declarations.serializers import normalize_fio_before_db_insert


from django.test import TestCase
import os


class SimpleImportTestCase(TestCase):

    def test_normalize_fio_before_db_insert(self):
        self.assertEqual(normalize_fio_before_db_insert('"Иванов Иван Иванович"'), "Иванов Иван Иванович")
        self.assertEqual(normalize_fio_before_db_insert("Иванов  Иван Иванович "), "Иванов Иван Иванович")
        self.assertEqual(normalize_fio_before_db_insert("12. Иванов Иван Иванович "), "Иванов Иван Иванович")

    def test_simple_import(self):
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()
        self.assertGreater(models.Office.objects.count(), 0)
        domains_folder = os.path.join(os.path.dirname(__file__), "domains")
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")
        permalinks_folder = os.path.dirname(__file__)

        section_count = 111999
        doc_old_id = 111110

        p = TPermaLinksSection(permalinks_folder)
        p.create_db()
        p.save_max_plus_one_primary_key(section_count)
        p.recreate_auto_increment_table()
        p.close_db()

        p = TPermaLinksSourceDocument(permalinks_folder)
        p.create_db()
        p.save_source_doc("f974dc82aa52acea2f9c49467e7395924605de474e76bafa85572351194b153a", doc_old_id)
        p.save_max_plus_one_primary_key(doc_old_id + 1)
        p.recreate_auto_increment_table()
        p.close_db()

        with SmartParserServerForTesting(sp_workdir, domains_folder):
            importer = ImportJsonCommand(None, None)
            input_path = os.path.join(os.path.dirname(__file__), "dlrobot_human.json")
            importer.handle(None, dlrobot_human=input_path, permalinks_folder=permalinks_folder)

        self.assertEqual(models.Source_Document.objects.count(), 1)
        self.assertEqual(list(models.Source_Document.objects.all())[0].id, doc_old_id)
        self.assertEqual(TPermaLinksSourceDocument(permalinks_folder).get_last_inserted_id_for_testing(), None)

        self.assertEqual(models.Section.objects.count(), 1)
        self.assertEqual(list(models.Section.objects.all())[0].id, section_count)
        self.assertEqual(TPermaLinksSection(permalinks_folder).get_last_inserted_id_for_testing(), section_count)

        self.assertEqual(models.RealEstate.objects.count(), 1)
        self.assertEqual(models.Income.objects.count(), 1)
        self.assertEqual(models.Income.objects.count(), 1)
        self.assertEqual(models.Income.objects.all()[:1].get().size, 1462642)
        self.assertGreater(models.Office.objects.count(), 0)

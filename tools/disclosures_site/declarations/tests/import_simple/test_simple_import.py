import declarations.models as models
from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
from declarations.management.commands.permalinks import TPermaLinksDB
from disclosures_site.declarations.tests.source_doc_for_testing import SourceDocServerForTesting
from declarations.management.commands.import_json import ImportJsonCommand


from django.test import TestCase
import os


class SimpleImportTestCase(TestCase):

    def test_simple_import(self):
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()
        self.assertGreater(models.Office.objects.count(), 0)
        domains_folder = os.path.join(os.path.dirname(__file__), "domains")
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")
        permalinks_path = os.path.join(os.path.dirname(__file__), "permalinks.dbm")

        section_count = 111999
        doc_old_id = 111110

        p = TPermaLinksDB(permalinks_path)
        p.create_db()

        p.save_max_plus_one_primary_key(models.Section, section_count)
        p.recreate_auto_increment_table(models.Section)

        src_doc = models.Source_Document(id=doc_old_id, sha256="f974dc82aa52acea2f9c49467e7395924605de474e76bafa85572351194b153a")
        p.save_source_doc(src_doc)
        p.save_max_plus_one_primary_key(models.Source_Document, doc_old_id + 1)
        p.recreate_auto_increment_table(models.Source_Document)
        p.close_db()

        with SmartParserServerForTesting(sp_workdir, domains_folder):
            importer = ImportJsonCommand(None, None)
            input_path = os.path.join(os.path.dirname(__file__), "dlrobot_human.json")
            importer.handle(None, dlrobot_human=input_path, permanent_links_db=permalinks_path)

        self.assertEqual(models.Source_Document.objects.count(), 1)
        self.assertEqual(list(models.Source_Document.objects.all())[0].id, doc_old_id)
        self.assertEqual(TPermaLinksDB(permalinks_path).get_new_max_id(models.Source_Document), None)

        self.assertEqual(models.Section.objects.count(), 1)
        self.assertEqual(list(models.Section.objects.all())[0].id, section_count)
        self.assertEqual(TPermaLinksDB(permalinks_path).get_new_max_id(models.Section), section_count)

        self.assertEqual(models.RealEstate.objects.count(), 1)
        self.assertEqual(models.Income.objects.count(), 1)
        self.assertEqual(models.Income.objects.count(), 1)
        self.assertEqual(models.Income.objects.all()[:1].get().size, 1462642)
        self.assertGreater(models.Office.objects.count(), 0)

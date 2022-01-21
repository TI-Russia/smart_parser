from declarations.management.commands.import_json import ImportJsonCommand
from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
from declarations.permalinks import TPermaLinksSourceDocument, TPermaLinksSection

from django.test import TestCase, tag
import os
import declarations.models as models


class DocOrderImportTestCase(TestCase):
    @tag('central')
    def test_doc_order_import(self):
        self.assertGreater(models.Office.objects.count(), 0)
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()

        permalinks_folder = os.path.dirname(__file__)
        TPermaLinksSection(permalinks_folder).create_and_save_empty_db()
        db = TPermaLinksSourceDocument(permalinks_folder)
        db.create_db()
        old_source_doc_id = 21
        db.save_source_doc("f974dc82aa52acea2f9c49467e7395924605de474e76bafa85572351194b153a", old_source_doc_id)
        db.save_max_plus_one_primary_key(old_source_doc_id + 1)
        db.recreate_auto_increment_table()
        db.close_db()

        domains_folder = os.path.join(os.path.dirname(__file__), "domains")
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")

        importer = ImportJsonCommand(None, None)
        os.chdir(os.path.dirname(__file__))

        with SmartParserServerForTesting(sp_workdir, domains_folder):
            importer.handle(None, dlrobot_human="dlrobot_human.json", smart_parser_human_json="human_jsons",
                            permalinks_folder=permalinks_folder)

        self.assertEqual(models.Source_Document.objects.count(), 2)
        self.assertEqual(models.Section.objects.count(), 1)
        section = models.Section.objects.all()[0]
        self.assertEqual(old_source_doc_id, section.source_document_id)

        doc_ids = list(d.id for d in models.Source_Document.objects.all())
        doc_ids.sort()
        self.assertListEqual([old_source_doc_id, old_source_doc_id+1], doc_ids)
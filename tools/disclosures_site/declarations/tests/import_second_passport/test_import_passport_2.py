from declarations.management.commands.import_json import ImportJsonCommand
from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
from declarations.permalinks import TPermalinksManager
from common.logging_wrapper import setup_logging
from common.primitives import build_dislosures_sha256
import declarations.models as models

from django.test import TestCase, tag
import os
import json


class SecondPassportImportTestCase(TestCase):
    @tag('central')
    def test_import_second_passport(self):
        self.assertGreater(models.Office.objects.count(), 0)
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()

        permalinks_folder = os.path.dirname(__file__)
        TPermalinksManager(setup_logging(), {'directory': permalinks_folder}).create_empty_dbs()

        domains_folder = os.path.join(os.path.dirname(__file__), "domains_1")
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")

        importer = ImportJsonCommand(None, None)
        os.chdir(os.path.dirname(__file__))

        with SmartParserServerForTesting(sp_workdir, domains_folder):
            importer.handle(None, dlrobot_human="dlrobot_human_1.json", smart_parser_human_json="human_jsons",
                            permalinks_folder=permalinks_folder)

        self.assertEqual(models.Section.objects.count(), 1)
        self.assertEqual(models.RealEstate.objects.count(), 6)
        self.assertEqual(models.Vehicle.objects.count(), 1)
        section_id1 = list(models.Section.objects.all())[0].id

        # one more time, but now we have two vehicles for the same person (same document), as though smart_parser
        # is more intelligent
        TPermalinksManager(setup_logging(), {'directory': permalinks_folder}).create_permalinks()

        # clear the db
        models.Vehicle.objects.all().delete()
        models.RealEstate.objects.all().delete()
        models.Income.objects.all().delete()
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()

        domains_folder = os.path.join(os.path.dirname(__file__), "domains_1")
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")

        importer = ImportJsonCommand(None, None)
        os.chdir(os.path.dirname(__file__))

        with SmartParserServerForTesting(sp_workdir, domains_folder) as sp_wrapper:
            sha256 = build_dislosures_sha256(os.path.join(os.path.dirname(__file__), "domains_1/test1.ru/fsin.docx"))
            sp_json = json.loads(sp_wrapper.server.get_smart_parser_json(sha256))
            assert len(sp_json['persons'][0]['vehicles']) == 1
            sp_json['persons'][0]['vehicles'] = list()
            sp_wrapper.server.register_built_smart_parser_json(sha256, json.dumps(sp_json).encode('utf8'))
            importer.handle(None, dlrobot_human="dlrobot_human_1.json", smart_parser_human_json="human_jsons",
                            permalinks_folder=permalinks_folder)

        self.assertEqual(models.Section.objects.count(), 1)
        self.assertEqual(models.RealEstate.objects.count(), 6)
        self.assertEqual(models.Vehicle.objects.count(), 0)
        section_id2 = list(models.Section.objects.all())[0].id

        self.assertEqual(section_id1, section_id2)

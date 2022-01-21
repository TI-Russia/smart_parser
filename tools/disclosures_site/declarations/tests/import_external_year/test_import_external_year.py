import declarations.models as models
from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
from declarations.permalinks import TPermalinksManager
from declarations.management.commands.import_json import ImportJsonCommand
from common.logging_wrapper import setup_logging

from django.test import TestCase, tag
import os


class ExternalYearImportTestCase(TestCase):
    @tag('central')
    def test_import_external_year(self):
        models.RealEstate.objects.all().delete()
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()
        self.assertGreater(models.Office.objects.count(), 0)
        domains_folder = os.path.join(os.path.dirname(__file__), "domains")
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")
        permalinks_folder = os.path.dirname(__file__)

        TPermalinksManager(setup_logging(), {'directory': permalinks_folder}).create_empty_dbs()

        with SmartParserServerForTesting(sp_workdir, domains_folder):
            importer = ImportJsonCommand(None, None)
            input_path = os.path.join(os.path.dirname(__file__), "dlrobot_human.json")
            importer.handle(None, dlrobot_human=input_path, permalinks_folder=permalinks_folder)

        self.assertEqual(models.Source_Document.objects.count(), 1)

        self.assertEqual(models.Section.objects.count(), 1)

        section = models.Section.objects.all()[0]
        self.assertEqual(section.income_year, 2014)

        realties = list(models.RealEstate.objects.all())
        self.assertEqual(4, len(realties))
        self.assertEqual(1, sum(1 for r in realties if r.owntype == models.OwnType.property_code))
        self.assertEqual(3, sum(1 for r in realties if r.owntype == models.OwnType.using_code))


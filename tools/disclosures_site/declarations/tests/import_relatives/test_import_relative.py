from declarations.management.commands.import_json import ImportJsonCommand
from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
from declarations.permalinks import TPermalinksManager
from common.logging_wrapper import setup_logging

from django.test import TestCase
import os
import declarations.models as models


class ComplexImportTestCase(TestCase):

    def test_import_with_relatives(self):
        self.assertGreater(models.Office.objects.count(), 0)
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()

        permalinks_folder = os.path.dirname(__file__)
        TPermalinksManager(setup_logging(), {'directory': permalinks_folder}).create_empty_dbs()

        domains_folder = os.path.join(os.path.dirname(__file__), "domains")
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")

        importer = ImportJsonCommand(None, None)
        os.chdir(os.path.dirname(__file__))

        with SmartParserServerForTesting(sp_workdir, domains_folder):
            importer.handle(None, dlrobot_human="dlrobot_human.json", smart_parser_human_json="human_jsons",
                            permalinks_folder=permalinks_folder)

        self.assertEqual(models.Section.objects.count(), 1)
        self.assertEqual(models.RealEstate.objects.count(), 6)

        # todo: real estates do not have relative_index, https://sokirko.atlassian.net/browse/DIS-133
        #relative_indices = set(r.relative_index for r in models.RealEstate.objects.all())
        #self.assertSetEqual(relative_indices, {None, 1, 2})
        #self.assertEqual(models.Income.objects.count(), 4)


        # машина принадлежит жене
        self.assertEqual(models.Vehicle.objects.count(), 1)
        self.assertEqual(models.Vehicle.objects.all()[0].relative, models.Relative.spouse_code)
        self.assertEqual(models.Vehicle.objects.all()[0].relative_index, 1)


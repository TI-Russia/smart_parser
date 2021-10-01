from declarations.management.commands.import_json import ImportJsonCommand
from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
from declarations.permalinks import TPermalinksManager
from common.logging_wrapper import setup_logging
from django.test import TestCase
import os
import declarations.models as models
from declarations.management.commands.create_permalink_storage import CreatePermalinksStorageCommand


class FsinImportTestCase(TestCase):

    def test_fsin_import(self):
        self.assertGreater(models.Office.objects.count(), 0)
        models.Income.objects.all().delete()
        models.RealEstate.objects.all().delete()
        models.Vehicle.objects.all().delete()
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()

        permalinks_folder = os.path.dirname(__file__)
        logger = setup_logging(log_file_name="test_fsin_import.log")
        TPermalinksManager(logger, {'directory': permalinks_folder}).create_empty_dbs()
        doc_folder = os.path.join(os.path.dirname(__file__), "domains")
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")

        importer = ImportJsonCommand(None, None)
        os.chdir(os.path.dirname(__file__))

        with SmartParserServerForTesting(sp_workdir, doc_folder):
            importer.handle(None, dlrobot_human="dlrobot_human.json", permalinks_folder=permalinks_folder)

        self.assertEqual(models.Section.objects.count(), 6)
        surname_to_office = {
            "Калашников А.П.": 482,
            "Романов Р.В.": 482,
            "Казан Ш.Т.": 3900,
            "Галиев Р.Т.": 3906,
            "Жамсаранов Ц.Л.": 3909,
            "Батыров Ю.М.": 3913
        }
        for s in models.Section.objects.all():
            self.assertEqual(surname_to_office[s.person_name], s.office_id, s.person_name)

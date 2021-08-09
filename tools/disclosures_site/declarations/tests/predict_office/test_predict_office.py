from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
import declarations.models as models
from disclosures_site.scripts.predict_office.predict_office import TOfficePredicter

from django.test import TestCase
import os


class TestPredictOffice(TestCase):
    def setUp(self):
        os.chdir(os.path.dirname(__file__))

    def check(self, predicter: TOfficePredicter, sha256, office_id):
        pred_office_id = predicter.dlrobot_human.document_collection[sha256].calculated_office_id
        self.assertEqual(office_id, pred_office_id)

    def test_predict_office(self):
        self.assertGreater(models.Office.objects.count(), 0)
        args = [
                '--dlrobot-human-path', "dlrobot_human.json"
                ]
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")
        doc_folder = os.path.join(os.path.dirname(__file__), "processed_projects")

        with SmartParserServerForTesting(sp_workdir, doc_folder):
            predicter = TOfficePredicter(TOfficePredicter.parse_args(args))
            predicter.predict_office()
            predicter.check()

        self.check(predicter, "e53861810867c308eba4ac4991f34c0bd10a25f49d675d069d426779a6f4a5f0", 5963)
        self.check(predicter, "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865", 4)
        self.check(predicter, "f0b5c2c2211c8d67ed15e75e656c7862d086e9245420892a7de62cd9ec582a06", 3913)


from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
import declarations.models as models
from predict_office.management.commands.predict_office import TOfficePredictor

from django.test import TestCase
import os


class TestPredictOffice(TestCase):
    def setUp(self):
        os.chdir(os.path.dirname(__file__))

    def check(self, predictor: TOfficePredictor, sha256, office_id):
        pred_office_id = predictor.dlrobot_human.get_document(sha256).calculated_office_id
        self.assertEqual(office_id, pred_office_id)

    def test_predict_office(self):
        self.assertGreater(models.Office.objects.count(), 0)
        options = {
                'dlrobot_human_path': "dlrobot_human.json"
        }
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")
        doc_folder = os.path.join(os.path.dirname(__file__), "processed_projects")

        with SmartParserServerForTesting(sp_workdir, doc_folder):
            predictor = TOfficePredictor(options)
            predictor.predict_office()
            predictor.check()

        #uncomment it if predict_office component goes to prod
        #self.check(predictor, "e53861810867c308eba4ac4991f34c0bd10a25f49d675d069d426779a6f4a5f0", 5963)

        self.check(predictor, "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865", 4)
        self.check(predictor, "f0b5c2c2211c8d67ed15e75e656c7862d086e9245420892a7de62cd9ec582a06", 3913)
        self.check(predictor, "unknownsha256308eba4ac4991f34c0bd10a25f49d675d069d426779a6f4a5f0", 5963)
        self.check(predictor, "87d086bde914d81f55316a970e4bfff3d117293ba3e15b4a856534b4ec137846", 1305)
        src_doc = predictor.dlrobot_human.get_document("87d086bde914d81f55316a970e4bfff3d117293ba3e15b4a856534b4ec137846")
        self.assertEqual(1, src_doc.region_id)
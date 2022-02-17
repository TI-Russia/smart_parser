from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
from predict_office.scripts.predict_office_dbm import TOfficePredictor

from unittest import TestCase
import os


class TestPredictOffice(TestCase):
    def setUp(self):
        os.chdir(os.path.dirname(__file__))

    def check(self, predictor: TOfficePredictor, sha256, office_id):
        js = predictor.dlrobot_human.get_document(sha256)
        pred_office_id = js.calculated_office_id
        self.assertEqual(office_id, pred_office_id)

    def test_predict_office(self):
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")
        doc_folder = os.path.join(os.path.dirname(__file__), "processed_projects")

        with SmartParserServerForTesting(sp_workdir, doc_folder):
            args = ["--dlrobot-human-path", "dlrobot_human.json"]
            predictor = TOfficePredictor(TOfficePredictor.parse_args(args))
            predictor.predict_office()
            predictor.check()

        self.check(predictor, "e53861810867c308eba4ac4991f34c0bd10a25f49d675d069d426779a6f4a5f0", 5963)
        self.check(predictor, "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865", 4)
        self.check(predictor, "f0b5c2c2211c8d67ed15e75e656c7862d086e9245420892a7de62cd9ec582a06", 3913)
        self.check(predictor, "unknownsha256308eba4ac4991f34c0bd10a25f49d675d069d426779a6f4a5f0", 5963)
        self.check(predictor, "87d086bde914d81f55316a970e4bfff3d117293ba3e15b4a856534b4ec137846", 1305)
        self.check(predictor, "0d52c7e5583d92e397179cf2dc6c95d46bd4e5a01ae533af7751cc61bd268a9c", 230)
        src_doc = predictor.dlrobot_human.get_document("87d086bde914d81f55316a970e4bfff3d117293ba3e15b4a856534b4ec137846")
        self.assertEqual(1, src_doc.region_id)
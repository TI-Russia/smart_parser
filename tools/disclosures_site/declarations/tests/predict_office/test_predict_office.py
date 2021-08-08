from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
import declarations.models as models
from disclosures_site.scripts.join_human_and_dlrobot import TJoiner

from django.test import TestCase
import json
import os

FAR_FUTURE = 5602811863

CANON_HUMAN_DLROBOT = {
    "document_folder": None,
    "documents": {
        "e53861810867c308eba4ac4991f34c0bd10a25f49d675d069d426779a6f4a5f0": {
            "file_ext": ".xlsx",
            "office_id": 5963,
            "w_refs": [
                {
                    "crawl_epoch": FAR_FUTURE,
                    "declaration_year": 2014,
                    "url": "http://mos.ru/some_link.xlsx",
                    "web_domain": "mos.ru/donm"
                }
            ]
        },
        "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865": {
            "d_refs": [
                {
                    "document_file_id": 1,
                    "document_id": 1,
                    "income_year": 2009,
                    "media_url": "https://declarator.org/media/documents/1.doc",
                    "office_id": 4,
                    "web_domain": "05.fsin.su"
                }
            ],
            "file_ext": ".xlsx",
            "office_id": 4,

        }
    }
}


class TestPredictOffice(TestCase):
    def setUp(self):
        os.chdir(os.path.dirname(__file__))
        self.dlrobot_human_path = "dlrobot_human.json"
        if os.path.exists(self.dlrobot_human_path):
            os.unlink(self.dlrobot_human_path)

    def test_predict_office(self):
        self.assertGreater(models.Office.objects.count(), 0)
        args = ['--max-ctime', str(FAR_FUTURE),
                '--input-dlrobot-folder', 'processed_projects',
                '--human-json', "human_files.json",
                '--output-json', self.dlrobot_human_path
                ]
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")
        doc_folder = os.path.join(os.path.dirname(__file__), "processed_projects")
        with SmartParserServerForTesting(sp_workdir, doc_folder):
            joiner = TJoiner(TJoiner.parse_args(args))
            joiner.main()
        with open(self.dlrobot_human_path) as inp:
            result_json = json.load(inp)
            for x in result_json['documents'].values():
                if 'office_strings' in x:
                    del x['office_strings']
            self.maxDiff = None
            self.assertDictEqual(CANON_HUMAN_DLROBOT, result_json)


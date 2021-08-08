from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting
import declarations.models as models
from disclosures_site.scripts.join_human_and_dlrobot import TJoiner

from django.test import TestCase
import os
import json

CANON_STATS = {
    "web_sites_count": 1,
    "files_count": 7,
    "both_found": 1,
    "only_human": 2,
    "only_dlrobot": 4,
    "crawl_epochs": {
        5602811863: 5,
        0: 2
    },
    "extensions": {
        ".xlsx": 7
    }
}

CANON_HUMAN_DLROBOT = {
    "document_folder": None,
    "documents": {
        "1121cfccd5913f0a63fec40a6ffd44ea64f9dc135c66634ba001d10bcf4302a2": {
            "file_ext": ".xlsx",
            "office_id": 3913,
            "w_refs": [
                {
                    "crawl_epoch": 5602811863,
                    "url": "http://05.fsin.su/old_dlrobot.xlsx",
                    "web_domain": "05.fsin.su"
                },
                {
                    "crawl_epoch": 0,
                    "url": "http://05.fsin.su/old_link1",
                    "web_domain": "05.fsin.su"
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
            "w_refs": [
                {
                    "crawl_epoch": 5602811863,
                    "declaration_year": 2014,
                    "url": "http://05.fsin.su/1984.xlsx",
                    "web_domain": "05.fsin.su"
                }
            ]
        },
        "53c234e5e8472b6ac51c1ae1cab3fe06fad053beb8ebfd8977b010655bfdd3c3": {
            "file_ext": ".xlsx",
            "office_id": 3913,
            "w_refs": [
                {
                    "crawl_epoch": 5602811863,
                    "url": "http://05.fsin.su/new_dlrobot.xlsx",
                    "web_domain": "05.fsin.su"
                },
                {
                    "crawl_epoch": 5602811863,
                    "url": "http://05.fsin.su/copy_dlrobot.xlsx",
                    "web_domain": "05.fsin.su"
                }
            ]
        },
        "7de1555df0c2700329e815b93b32c571c3ea54dc967b89e81ab73b9972b72d1d": {
            "d_refs": [
                {
                    "document_file_id": 1432,
                    "document_id": 19,
                    "income_year": 2009,
                    "media_url": "https://declarator.org/media/documents/2.doc",
                    "office_id": 4,
                    "web_domain": "05.fsin.su"
                }
            ],
            "file_ext": ".xlsx",
            "office_id": 4
        },
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855": {
            "d_refs": [
                {
                    "document_file_id": 1,
                    "document_id": 60000,
                    "income_year": 2009,
                    "media_url": "https://declarator.org/human_file_deleted_on_site/1.doc",
                    "office_id": 4,
                    "web_domain": "05.fsin.su"
                }
            ],
            "file_ext": ".xlsx",
            "office_id": 4
        },
        "f0b5c2c2211c8d67ed15e75e656c7862d086e9245420892a7de62cd9ec582a06": {
            "file_ext": ".xlsx",
            "office_id": 3913,
            "w_refs": [
                {
                    "crawl_epoch": 0,
                    "url": "http://05.fsin.su/old_link2",
                    "web_domain": "05.fsin.su"
                }
            ]
        },
        "fa8bd40933bf21520b3b664b0d7507919426cbd7a86a84238c400b93b3bf4d00": {
            "file_ext": ".xlsx",
            "office_id": 3913,
            "w_refs": [
                {
                    "crawl_epoch": 5602811863,
                    "url": "http://05.fsin.su/new_dlrobot.xlsx",
                    "web_domain": "05.fsin.su"
                }
            ]
        }
    }
}


class JoinDLrobotAndHuman(TestCase):
    def setUp(self):
        os.chdir(os.path.dirname(__file__))
        self.dlrobot_human_path = "dlrobot_human.json"
        if os.path.exists(self.dlrobot_human_path):
            os.unlink(self.dlrobot_human_path)

    def test_join_dlrobot_and_human(self):
        self.assertGreater(models.Office.objects.count(), 0)
        args = ['--max-ctime', '5602811863', #the far future
                '--input-dlrobot-folder', 'processed_projects',
                '--human-json', "human_files.json",
                '--old-dlrobot-human-json', 'old/dlrobot_human.json',
                '--output-json', self.dlrobot_human_path
                ]
        sp_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_server")
        doc_folder = os.path.join(os.path.dirname(__file__), "processed_projects")
        with SmartParserServerForTesting(sp_workdir, doc_folder):
            joiner = TJoiner(TJoiner.parse_args(args))
            joiner.main()
        stats = joiner.output_dlrobot_human.get_stats()
        self.assertDictEqual(CANON_STATS,  stats)
        with open(self.dlrobot_human_path) as inp:
            result_json = json.load(inp)
            self.maxDiff = None
            self.assertDictEqual(CANON_HUMAN_DLROBOT, result_json)


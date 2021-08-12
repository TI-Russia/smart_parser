from disclosures_site.scripts.export_human_files import TExportHumanFiles
from disclosures_site.declarations.tests.source_doc_for_testing import SourceDocServerForTesting
from declarations.tests.smart_parser_for_testing import SmartParserServerForTesting

from django.test import TestCase
import os
import json
import time

canon_json_4915 = {
    "documents": {
        "7b7995e792823a1daa65008a8045677c052338eb7052dac09029f19ce2fd7a00": {
            "d_refs": [
                {
                    "document_file_id": 4915,
                    "document_id": 13,
                    "income_year": 2009,
                    "media_url": "https://declarator.org/media/documents/doxod%2520prokurorov%2520za%25202009.doc",
                    "office_id": 19,
                    "web_domain": "vladprok.ru"
                }
            ],
            "file_ext": ".doc",
            "office_id": None
        }
    }
}

canon_json_10282 = {
    "documents": {
        "0edf0040508a60f28042d9c4e19e436825bc9e4248b70a36bb27da4481f27c0c": {
            "d_refs": [
                {
                    "document_file_id": 10282,
                    "document_id": 7422,
                    "income_year": 2011,
                    "media_url": "https://declarator.org/media/documents/deklaraciya_2012.pdf",
                    "office_id": 3062,
                    "web_domain": "adm-kletnya.ru"
                }
            ],
            "file_ext": ".pdf",
            "office_id": None
        }
    }
}


class ExportHuman(TestCase):
    def setUp(self):
        os.chdir(os.path.dirname(__file__))

    def run_cmd(self, cmd):
        exit_value = os.system(cmd)
        self.assertEqual(exit_value,  0)

    def common_test(self, document_file_id, canon_json):
        output_json = "human_files.json"
        arg_list = ['--document-file-id', str(document_file_id), '--table', 'declarations_documentfile',
                    '--dlrobot-human-json', output_json, '--start-from-an-empty-file']
        source_doc_workdir = os.path.join(os.path.dirname(__file__), "source_doc")
        smart_parser_workdir = os.path.join(os.path.dirname(__file__), "smart_parser_workdir")
        with SourceDocServerForTesting(source_doc_workdir) as source_doc_wrapper:
            with SmartParserServerForTesting(smart_parser_workdir) as smart_parser_server:
                args = TExportHumanFiles.parse_args(arg_list)
                with TExportHumanFiles(args) as exporter:
                    exporter.export_files()
                    smart_parser_server.server.task_queue.join()
                self.assertEqual(source_doc_wrapper.server.get_stats()['source_doc_count'], 1)
                json.dumps(canon_json, indent=4, ensure_ascii=False)
                with open (output_json) as inp:
                    result_json = json.load(inp)
                    self.assertDictEqual(canon_json, result_json)
                time.sleep(2)
                self.assertEqual(smart_parser_server.server.get_stats()['session_write_count'], 1)

    def test_4915(self):
        self.common_test(4915, canon_json_4915)

    def test_10282(self):
        self.common_test(10282, canon_json_10282)



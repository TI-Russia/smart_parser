from django.test import TestCase
from scripts.access_log_squeeze import TAccessLogReader
import os


class TestAccessLogSqueeze(TestCase):

    def test_access_log_squeeze(self):
        output = os.path.join(os.path.dirname(__file__), "access_log_squeeze.txt")
        args = TAccessLogReader.parse_args([
            '--access-log-folder', os.path.join(os.path.dirname(__file__), "logs"),
            '--output-path', output
        ])
        sq = TAccessLogReader(args)
        sq.build_popular_site_pages()

        with open(output) as inp:
            lines = inp.readlines()
            self.assertEqual(1, len(lines))


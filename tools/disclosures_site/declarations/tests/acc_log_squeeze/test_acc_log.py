from django.test import TestCase
from declarations.management.commands.access_log_squeeze import AccessLogSqueezer
import json
import os
import argparse


class TestAccessLogSqueeze(TestCase):

    def test_access_log_squeeze(self):
        sq = AccessLogSqueezer(None, None)
        output = os.path.join(os.path.dirname(__file__), "access_log_squeeze.txt")
        parser = argparse.ArgumentParser()
        sq.add_arguments(parser)
        args = parser.parse_args([
            '--access-log-folder', os.path.join(os.path.dirname(__file__), "logs"),
            '--output-path', output
        ])
        sq.handle(None, **args.__dict__)

        with open(output) as inp:
            lines = inp.readlines()
            self.assertEqual(1, len(lines))


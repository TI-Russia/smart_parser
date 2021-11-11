from unittest import TestCase

from common.urllib_parse_pro import site_url_to_file_name

class UrlToFileTest(TestCase):

    def test_site_url_to_file_name(self):
        # use urlpath in file names, otherwise it can be race condition
        s = site_url_to_file_name("mos.ru/donm")
        self.assertEqual("mos.ru_donm", s)

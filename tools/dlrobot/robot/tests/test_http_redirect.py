from common.http_request import THttpRequester
from common.download import TDownloadedFile
from common.logging_wrapper import setup_logging
from unittest import TestCase


class TestRecursion(TestCase):
    def test_redirect_popular_site(self):
        THttpRequester.initialize(setup_logging())
        redirected_url, headers = THttpRequester.request_url_headers_with_global_cache("http://www.meduza.io")
        self.assertIsNotNone(headers)
        self.assertEqual(redirected_url, 'https://meduza.io/')

    def test_gibdd(self):
        try:
            THttpRequester.initialize(setup_logging())
            s = THttpRequester.make_http_request("http://gibdd.ru", "GET")
        except THttpRequester.RobotHttpException as exp:
            self.assertEqual(exp.http_code, 520)
            # todo: why urlib cannot resolve redirects for http://gibdd.ru  -> гибдд.рф?

    def test_unicode(self):

        try:
            THttpRequester.initialize(setup_logging())
            s = THttpRequester.make_http_request("http://5%20июня%20запретят%20розничную%20продажу%20алкоголя", "GET")
        except THttpRequester.RobotHttpException as exp:
            # no UnicodeException for this url
            pass

    def test_gibdd(self):
        try:
            THttpRequester.initialize(setup_logging())
            s = THttpRequester.make_http_request("http://gibdd.ru", "GET")
        except THttpRequester.RobotHttpException as exp:
            self.assertEqual(exp.http_code, 520)
            # todo: why urlib cannot resolve redirects for http://gibdd.ru  -> гибдд.рф?


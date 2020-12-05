from unittest import TestCase
from common.http_request import request_url_headers_with_global_cache, make_http_request, RobotHttpException
import logging


class TestRecursion(TestCase):
    def test_yandex(self):
        redirected_url, headers = request_url_headers_with_global_cache(logging, "www.yandex.ru")
        self.assertIsNotNone(headers)
        self.assertEqual(redirected_url, 'https://yandex.ru/')

    def test_gibdd(self):
        try:
            s = make_http_request(logging, "http://gibdd.ru", "GET")
        except RobotHttpException as exp:
            self.assertEqual(exp.http_code, 520)
            # todo: why urlib cannot resolve redirects for http://gibdd.ru  -> гибдд.рф?

    def test_unicode(self):

        try:
            s = make_http_request(logging, "http://5%20июня%20запретят%20розничную%20продажу%20алкоголя", "GET")
        except RobotHttpException as exp:
            # no UnicodeException for this url
            pass





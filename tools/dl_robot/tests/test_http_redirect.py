from unittest import TestCase
from common.http_request import request_url_headers_with_global_cache, make_http_request, RobotHttpException
from common.download import TDownloadedFile
import logging


class TestRecursion(TestCase):
    def test_yandex(self):
        redirected_url, headers = request_url_headers_with_global_cache(logging, "http://www.yandex.ru")
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

    def test_gibdd(self):
        try:
            s = make_http_request(logging, "http://gibdd.ru", "GET")
        except RobotHttpException as exp:
            self.assertEqual(exp.http_code, 520)
            # todo: why urlib cannot resolve redirects for http://gibdd.ru  -> гибдд.рф?

    def test_js_redirect1(self):
        html = """
        div class="photo-item-cover-block-outside">
			<div class="photo-item-cover-block-container">
				<div class="photo-item-cover-block-outer">
					<div class="photo-item-cover-block-inner">
						<div class="photo-item-cover-block-inside">
							<div class="photo-item-cover photo-album-avatar " id="photo_album_cover_381" title="Работы победителей конкурса антикоррупционной направленности «Давайте жить честно»"
																	style="background-image:url('/upload/iblock/107/iblock_section_381.jpg');"
																									onclick="window.location='/index.php?PAGE_NAME=section&amp;SECTION_ID=381';"
																>
															</div>
						</div>
					</div>
				</div>
			</div>
        """
        self.assertIsNone(TDownloadedFile.get_simple_js_redirect("http://www.aot.ru", html))

    def test_js_redirect2(self):
        html = """
        <html>
        <script>
            window.location.href = 'newPage.html';
        </script>
        </html>
        """
        redirect = TDownloadedFile.get_simple_js_redirect("http://www.aot.ru", html)
        self.assertEqual(redirect, "http://www.aot.ru/newPage.html")


    def test_js_redirect3(self):
        html = """
        <html>
        <script>
            window.location= 'http://www.aot.ru/newPage.html';
        </script>
        </html>
        """
        redirect = TDownloadedFile.get_simple_js_redirect("http://www.aot.ru", html)
        self.assertEqual(redirect, "http://www.aot.ru/newPage.html")

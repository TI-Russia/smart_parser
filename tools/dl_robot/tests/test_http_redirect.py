from common.http_request import THttpRequester
from common.download import TDownloadedFile
from common.logging_wrapper import setup_logging
from unittest import TestCase


class TestRecursion(TestCase):
    def test_yandex_redirect(self):
        THttpRequester.initialize(setup_logging())
        redirected_url, headers = THttpRequester.request_url_headers_with_global_cache("http://www.yandex.ru")
        self.assertIsNotNone(headers)
        self.assertEqual(redirected_url, 'https://yandex.ru/')

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
        THttpRequester.initialize(setup_logging())
        self.assertIsNone(TDownloadedFile.get_simple_js_redirect("http://www.aot.ru", html))

    # too dangerous (see "window.location = a.href;" in http://батайск-официальный.рф)
    # def test_js_redirect2(self):
    #     html = """
    #     <html>
    #     <script>
    #         window.location.href = 'newPage.html';
    #     </script>
    #     </html>
    #     """
    #     redirect = TDownloadedFile.get_simple_js_redirect("http://www.aot.ru", html)
    #     self.assertEqual(redirect, "http://www.aot.ru/newPage.html")


    def test_js_redirect3(self):
        html = """
        <html>
        <script>
            window.location= 'http://www.aot.ru/newPage.html';
        </script>
        </html>
        """
        THttpRequester.initialize(setup_logging())
        redirect = TDownloadedFile.get_simple_js_redirect("http://www.aot.ru", html)
        self.assertEqual(redirect, "http://www.aot.ru/newPage.html")

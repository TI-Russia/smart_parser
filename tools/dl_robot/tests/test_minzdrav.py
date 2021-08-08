from dl_robot.tests.selenium_for_tests import TestDeclarationLinkSelenium
from common.http_request import THttpRequester


class TestMinzdrav(TestDeclarationLinkSelenium):

    def setUp(self):
        super().setUp("web_sites/minzdrav1")

    def tearDown(self):
        super().tearDown()
        #pass

    def test_minzdrav(self):
        # кажется, тест не очень стабилен, попробую так изменить THttpRequester.HTTP_TIMEOUT
        # пользуется ли browser head запросами?
        #THttpRequester.HTTP_TIMEOUT = 60

        url = 'https://minzdrav.gov.ru/ministry/61/0/materialy-po-deyatelnosti-departamenta/combating_corruption/6/svedeniya-o-dohodah-rashodah-ob-imuschestve-i-obyazatelstvah-imuschestvennogo-haraktera-predstavlennye-federalnymi-gosudarstvennymi-grazhdanskimi-sluzhaschimi-ministerstva-zdravoohraneniya-rossiyskoy-federatsii-za-otchetnyy-period-s-1-yanvarya-2016-goda-po-31-dekabrya-2016-goda'
        found_links = self.collect_links_selenium(url, is_last_step=True)
        self.assertGreater(len(found_links), 0)
        downloaded_files = list(k for k in found_links.keys() if k.find('/attaches/') != -1)
        self.assertEqual(2, len(downloaded_files))


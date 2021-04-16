from unittest import TestCase
from web_site_db.robot_step import web_link_is_absolutely_prohibited
from common.download import TDownloadEnv
from common.logging_wrapper import setup_logging
import os
import tempfile


BAD_LINKS = [
("www.mvd.ru", "www.yandex.ru", True),
("www.mvd.ru", "mvd.ru", False),
("www.mvd.ru", "www.mvd.ru/print=1", True),
("bagaev.donland.ru", "donland.ru", False),
("kraevoy.hbr.sudrf.ru", "files.sudrf.ru", False),
("kremlin.ru", "static.kremlin.ru", False),
("ksl.spb.sudrf.ru", "files.sudrf.ru", False),
("mil.ru", "recrut.mil.ru", False),
("mil.ru", "stat.mil.ru", False),
("minpromtorg.gov.ru", "gossluzhba.gov.ru", True),
("minpromtorg.gov.ru", "pravo.gov.ru", True),
("minvostokrazvitia.ru", "data.gov.ru", True),
("minvostokrazvitia.ru", "gossluzhba.gov.ru", True),
("minvostokrazvitia.ru", "minvr.ru", False),
("minvostokrazvitia.ru", "publication.pravo.gov.ru", True),
("minvr.ru", "minvostokrazvitia.ru", False),
("oblsud.tula.sudrf.ru", "files.sudrf.ru", False),
("oblsud.tula.sudrf.ru", "kremlin.ru", True),
("oren-rshn.ru", "fsvps.ru", True),
("oren-rshn.ru", "pravo.gov.ru", True),
("rosminzdrav.ru", "pravo.gov.ru", True),
("rosminzdrav.ru", "static-0.rosminzdrav.ru", False),
("rosminzdrav.ru", "static-1.rosminzdrav.ru", False),
("rosminzdrav.ru", "static-2.rosminzdrav.ru", False),
("rosminzdrav.ru", "static-3.rosminzdrav.ru", False),
("stat.mil.ru", "mil.ru", False),
("stat.mil.ru", "recrut.mil.ru", False),
("voronovskoe.ru", "trud.mos.ru", True),
("https://minvr.ru/press-center/collegium/5197/", "http://vk.com/share.php?url=https://minvr.ru:443/press-center/collegium/5197/", True),
("https://oren-rshn.ru:443", "https://oren-rshn.ru", False),
("http://adm.ugorsk.ru/about/vacancies/information_about_income/?SECTION_ID=5244&ELEMENT_ID=79278", "http://adm.ugorsk.ru/bitrix/redirect.php?event1=catalog_out&amp;event2=%2Fupload%2Fiblock%2Fb59%2Fb59f80e6eaf7348f74e713219c169a24.pdf&amp;event3=%D0%9F%D0%B5%D1%87%D0%B5%D0%BD%D0%B5%D0%B2%D0%B0+%D0%9D%D0%98.pdf&amp;goto=%2Fupload%2Fiblock%2Fb59%2Fb59f80e6eaf7348f74e713219c169a24.pdf", False),
]


class TestProhibitedLinks(TestCase):
    def test_prohibited_links(self):
        logger = setup_logging('test_prohibited')
        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__), prefix="cached_prohibited.") as tmp_folder:
            TDownloadEnv.FILE_CACHE_FOLDER = str(tmp_folder)
            for (source, target, is_prohibited) in BAD_LINKS:
                if not source.startswith('http'):
                    source = 'http://' + source
                if not target.startswith('http'):
                    target = 'http://' + target
                self.assertEqual(is_prohibited, web_link_is_absolutely_prohibited(logger, source, target))

from web_site_db.robot_step import TRobotStep
from common.download import TDownloadEnv
from common.logging_wrapper import setup_logging
from web_site_db.robot_project import TRobotProject
from common.link_info import TLinkInfo, TClickEngine

import os
import shutil
from unittest import TestCase


class TestProhibitedLinksBase(TestCase):
    def setup_project(self, morda_url):
        logger = setup_logging('prohibited')
        self.project = TRobotProject(logger, '', [], "result", enable_search_engine=False)
        web_site = self.project.add_web_site(morda_url)
        self.robot_step = TRobotStep(web_site)

        d = os.path.join(os.path.dirname(__file__), "data.prohibited")
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
        os.mkdir(d)
        TDownloadEnv.FILE_CACHE_FOLDER = d

    def tearDown(self):
        shutil.rmtree(TDownloadEnv.FILE_CACHE_FOLDER, ignore_errors=True)

    def check_follow(self, src, trg, canon):
        if not src.startswith('http'):
            src = 'http://' + src
        if not trg.startswith('http'):
            trg = 'http://' + trg
        link_info = TLinkInfo(TClickEngine.selenium, src, trg)
        can_follow = self.robot_step.can_follow_this_link(link_info)
        self.assertEqual(canon, can_follow, msg="{} -> {}".format(src, trg))


class TestProhibitedLinks(TestProhibitedLinksBase):
    def setUp(self):
        self.setup_project("aot.ru")

    def test_prohibit_popular_sites(self):
        pairs = [
            ("https://minvr.ru/press-center/collegium/5197/", "http://vk.com/share.php?url=https://minvr.ru:443"),
            ("www.mvd.ru", "www.yandex.ru")
        ]
        for (source, target) in pairs:
            self.check_follow(source, target, False)

    def test_prohibit_special_versions(self):
        pairs = [
            ("www.mvd.ru", "www.mvd.ru/test.html?print=1"),
            ("http://www.admkrsk.ru/Pages/default.aspx",
             "http://www.admkrsk.ru/city/areas/kir/Pages/incomes.aspx?accessability=on&spacing=3"),
        ]
        for (source, target) in pairs:
            self.check_follow(source, target, False)

    def test_redirects(self):
        pairs = [
            ("rosminzdrav.ru/bb", "https://minzdrav.gov.ru/aaa"),
            ('static-0.minzdrav.gov.ru/aaa', 'rosminzdrav.ru/bbb')
        ]
        for (source, target) in pairs:
            self.check_follow(source, target, True)

    def test_follow_subdomain(self):
        sub_domains = [
            ("kremlin.ru",
             "http://static.kremlin.ru/media/events/video/ru/video_low/pTDBQFBtXkyepP0XncNk0GVvTNuwPaLo.mp4"),
            ("bagaev.donland.ru", "donland.ru"),
            ("kraevoy.hbr.sudrf.ru", "files.sudrf.ru"),
            ("ksl.spb.sudrf.ru", "files.sudrf.ru"),
            ("mil.ru", "recrut.mil.ru"),
            ("mil.ru", "stat.mil.ru"),
            ("oblsud.tula.sudrf.ru", "files.sudrf.ru"),
            ("rosminzdrav.ru", "static-0.rosminzdrav.ru"),
            ("static-1.rosminzdrav.ru", "rosminzdrav.ru"),
            ("stat.mil.ru", "mil.ru"),
            ("stat.mil.ru", "recrut.mil.ru"),
            ("https://oren-rshn.ru:443", "https://oren-rshn.ru"),
            ("http://adm.ugorsk.ru/about/vacancies/information_about_income/?SECTION_ID=5244&ELEMENT_ID=79278",
             "http://adm.ugorsk.ru/bitrix/redirect.php?event1=catalog_out&amp;event2=%2Fupload%2Fiblock%2Fb59%2Fb59f80e6eaf7348f74e713219c169a24.pdf&amp;event3=%D0%9F%D0%B5%D1%87%D0%B5%D0%BD%D0%B5%D0%B2%D0%B0+%D0%9D%D0%98.pdf&amp;goto=%2Fupload%2Fiblock%2Fb59%2Fb59f80e6eaf7348f74e713219c169a24.pdf"),
        ]
        for (source, target) in sub_domains:
            self.check_follow(source, target, True)

    def test_prohibited_links(self):
        pairs = [
            ("minpromtorg.gov.ru", "gossluzhba.gov.ru"),
            ("minpromtorg.gov.ru", "pravo.gov.ru"),
            ("minvostokrazvitia.ru", "data.gov.ru"),
            ("minvostokrazvitia.ru", "gossluzhba.gov.ru"),
            ("minvostokrazvitia.ru", "publication.pravo.gov.ru"),
            ("oblsud.tula.sudrf.ru", "kremlin.ru"),
            ("oren-rshn.ru", "fsvps.ru"),
            ("oren-rshn.ru", "pravo.gov.ru"),
            ("rosminzdrav.ru", "pravo.gov.ru"),
            ("voronovskoe.ru", "trud.mos.ru"),
        ]
        for source, target in pairs:
            self.check_follow(source, target, False)


class TestProhibitedLinksMosRu(TestProhibitedLinksBase):

    def setUp(self):
        self.setup_project("mos.ru/findep")

    def test_other_projects_links(self):

        self.check_follow("http://mos.ru/findep", "http://mos.ru/findep/aaaa", True)
        self.check_follow("http://mos.ru/findep", "http://mos.ru/unknown_path", True)
        self.check_follow("http://mos.ru/findep", "http://mos.ru/upload", True)
        self.check_follow("http://mos.ru/findep", "http://upload.mos.ru", True)

        self.check_follow("http://mos.ru/findep", "http://mos.ru/kultura111", True) # unknown path
        self.check_follow("http://mos.ru/findep", "http://mos.ru/kultura", False) #other project
        self.check_follow("http://mos.ru/findep", "http://mos.ru/kultura/", False) #other project

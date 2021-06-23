from bs4 import BeautifulSoup
import urllib

#see https://stackoverflow.com/questions/31528600/beautifulsoup-runtimeerror-maximum-recursion-depth-exceeded
import sys
sys.setrecursionlimit(10000)


class THtmlParser:
    def __init__(self, file_data, url=None):
        self.url = url
        self.file_data = file_data
        self.soup = BeautifulSoup(self.file_data, "html.parser")
        self.html_with_markup = str(self.soup)
        self.page_title = self.soup.title.string if self.soup.title is not None else ""
        self.base = None
        if url is not None:
            self.base = self.get_base_url()

    def get_plain_text(self):
        return self.soup.get_text()

    @staticmethod
    def make_link(main_url, href):
        url = urllib.parse.urljoin(main_url, href)

        # we cannot disable html anchors because it is used as ajax requests:
        # https://developers.google.com/search/docs/ajax-crawling/docs/specification?csw=1
        # see an example of ajax urls in
        # 1. http://minpromtorg.gov.ru/open_ministry/anti/activities/info/
        #    -> https://minpromtorg.gov.ru/docs/#!svedeniya_o_dohodah_rashodah_ob_imushhestve_i_obyazatelstvah_imushhestvennogo_haraktera_federalnyh_gosudarstvennyh_grazhdanskih_sluzhashhih_minpromtorga_rossii_rukovodstvo_a_takzhe_ih_suprugi_supruga_i_nesovershennoletnih_detey_za_period_s_1_yanvarya_2019_g_po_31_dekabrya_2019_g
        # 2. https://minzdrav.gov.ru/ministry/61/0/materialy-po-deyatelnosti-departamenta/combating_corruption/6/4/2
        #    -> https://minzdrav.gov.ru/ministry/61/0/materialy-po-deyatelnosti-departamenta/combating_corruption/6/4/2#downloadable
        # i = url.find('#')
        # if i != -1:
        #    url = url[0:i]
        return url

    def make_link_soup(self, href):
        return THtmlParser.make_link(self.base, href)

    def get_base_url(self):
        base = self.url
        for l in self.soup.findAll('base'):
            href = l.attrs.get('href')
            if href is not None:
                base = href
                break
        if base.startswith('/'):
            base = make_link(main_url, base)

        return base

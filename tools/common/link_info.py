from DeclDocRecognizer.dlrecognizer import DL_RECOGNIZER_ENUM
from common.primitives import normalize_and_russify_anchor_text, strip_html_url


class TClickEngine:
    urllib = 'urllib'
    selenium = 'selenium'
    google = 'google'
    manual = 'manual'
    sitemap_xml = 'sitemap_xml'

    @staticmethod
    def is_search_engine(s):
        return s == "google"


class TLinkInfo:
    MINIMAL_LINK_WEIGHT = 0.0
    TRASH_LINK_WEIGHT = 5.0
    NORMAL_LINK_WEIGHT = 10.0  # these links should be processed in normal case, if weight is less, then we can stop crawling
    BEST_LINK_WEIGHT = 50.0

    def __init__(self, engine, source_url,  target_url, source_html="", element_index=0, anchor_text="",
                 tag_name=None, source_page_title=None, element_class=None):
        self.engine = engine
        self.element_index = element_index
        self.page_html = "" if source_html is None else source_html
        self.source_url = source_url
        self.target_url = target_url
        self.anchor_text = ""
        self.set_anchor_text(anchor_text)
        self.tag_name = tag_name
        self.text_proxim = False
        self.downloaded_file = None
        self.target_title = None
        self.weight = TLinkInfo.MINIMAL_LINK_WEIGHT
        self.dl_recognizer_result = DL_RECOGNIZER_ENUM.UNKNOWN
        self.element_class = element_class
        self.source_page_title = source_page_title
        if self.source_page_title is None:
            self.source_page_title = ""

    def set_anchor_text(self, anchor_text):
        self.anchor_text = '' if anchor_text is None else anchor_text.strip(" \r\n\t")

    def to_json(self):
        rec = {
            'src': self.source_url,
            'trg': self.target_url,
            'text': self.anchor_text,
            'engine': self.engine,
            'element_index': self.element_index,
        }
        if self.tag_name is not None:
            rec['tagname'] = self.tag_name
        if self.text_proxim:
            rec['text_proxim'] = True
        if self.downloaded_file is not None:
            rec['downloaded_file'] = self.downloaded_file
        if self.weight != TLinkInfo.MINIMAL_LINK_WEIGHT:
            rec['link_weight'] = self.weight
        if self.dl_recognizer_result != DL_RECOGNIZER_ENUM.UNKNOWN:
            rec['dl_recognizer_result'] = self.dl_recognizer_result
        return rec

    def from_json(self, rec):
        self.source_url = rec['src']
        self.target_url = rec['trg']
        self.anchor_text = rec['text']
        self.engine = rec['engine']
        self.element_index = rec['element_index']
        self.tag_name = rec.get('tagname')
        self.text_proxim = rec.get('text_proxim', False)
        self.downloaded_file = rec.get('downloaded_file')
        self.weight = rec.get('link_weight', TLinkInfo.MINIMAL_LINK_WEIGHT)
        self.dl_recognizer_result = rec.get('dl_recognizer_result', DL_RECOGNIZER_ENUM.UNKNOWN)
        return self


def check_link_sitemap(logger, link_info: TLinkInfo):
    text = normalize_and_russify_anchor_text(link_info.anchor_text)
    return text.startswith('карта сайта')


def check_anticorr_link_text(logger, link_info: TLinkInfo):
    text = link_info.anchor_text.strip().lower()
    if text.find('антикоррупционная комиссия') != -1:
        link_info.weight = 5
        return True

    if text.startswith(u'противодействие') or text.startswith(u'борьба') or text.startswith(u'нет'):
        if text.find("коррупц") != -1:
            link_info.weight = 5
            return True
    return False


def check_anticorr_link_text_2(logger, link_info: TLinkInfo):
    text = link_info.anchor_text.strip().lower()
    if text.find("отчеты") != -1:
        link_info.weight = 5
        return True
    return False

def check_sub_page_or_iframe(logger,  link_info: TLinkInfo):
    if link_info.target_url is None:
        return False
    if link_info.tag_name is not None and link_info.tag_name.lower() == "iframe":
        return True
    parent = strip_html_url(link_info.source_url)
    subpage = strip_html_url(link_info.target_url)
    return subpage.startswith(parent)

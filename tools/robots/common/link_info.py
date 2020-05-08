from DeclDocRecognizer.dlrecognizer import DL_RECOGNIZER_ENUM


class TClickEngine:
    urllib = 'urllib'
    selenium = 'selenium'
    google = 'google'
    manual = 'manual'

    @staticmethod
    def is_search_engine(s):
        return s == "google"

class TLinkInfo:
    MINIMAL_LINK_WEIGHT = 0.0
    TRASH_LINK_WEIGHT = 5.0
    NORMAL_LINK_WEIGHT = 10.0  # these links should be processed in normal case, if weight is less, then we can stop crawling
    BEST_LINK_WEIGHT = 50.0

    def __init__(self, engine, source, target, page_html="", element_index=0, anchor_text="", tag_name=None):
        self.engine = engine
        self.element_index = element_index
        self.page_html = "" if page_html is None else page_html
        self.source_url = source
        self.target_url = target
        self.anchor_text = ""
        self.set_anchor_text(anchor_text)
        self.tag_name = tag_name
        self.text_proxim = False
        self.downloaded_file = None
        self.target_title = None
        self.weight = TLinkInfo.MINIMAL_LINK_WEIGHT
        self.dl_recognizer_result = DL_RECOGNIZER_ENUM.UNKNOWN

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

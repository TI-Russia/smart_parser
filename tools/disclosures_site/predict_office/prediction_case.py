from declarations.input_document import TWebReference, TSourceDocument

import json


class TPredictionCase:
    def __init__(self, office_index=None, sha256=None, web_domain=None, true_office_id=None, office_strings=None):
        self.office_index = office_index
        self.sha256 = sha256
        self.office_strings = office_strings
        self.web_domain = web_domain
        self.text = self.get_text_from_office_strings()

        self.true_office_id = true_office_id
        if self.true_office_id is not None and office_index is not None:
            self.true_region_id = office_index.get_office_region(self.true_office_id)
        else:
            self.true_region_id = None

    @staticmethod
    def truncate_title(title):
        normal_title_len = 500
        context_size = 60
        if title is None or len(title) <= normal_title_len:
            return False, title

        lower_title = title.lower()
        title_start = lower_title.find('сведения')
        if title_start == -1:
            title_start = lower_title.find('c в е д')
        if title_start != -1:
            title_start = max(0, title_start - context_size)
            title_end = lower_title.find('фамилия', title_start)
            if title_end < 300:
                title_end = title_start + normal_title_len + 2 * context_size
            title = title[title_start: title_end]
            return True, title
        return False, title

    def get_text_from_office_strings(self):
        if self.office_strings is None or len(self.office_strings) == 0:
            return ""
        office_strings = json.loads(self.office_strings)
        if "smart_parser_data_not_found"  in office_strings:
            return ""
        text = ""
        title = office_strings['title']

        if title is not None and len(title) > 0:
             text += title + " "
        for t in office_strings['roles']:
            if len(t) > 0:
                text += t + " "
        for t in office_strings['departments']:
            if len(t) > 0:
                text += t + " "
        return text.strip()

    def from_json(self, js):
        js = json.loads(js)
        self.sha256 = js['sha256']
        self.web_domain = js['web_domain']
        self.true_office_id = js['true_office_id']
        self.office_strings = js['office_strings']
        self.true_region_id = self.office_index.get_office_region(self.true_office_id)
        self.text = self.get_text_from_office_strings()

    def to_json(self, js):
        js = {
            'sha256': self.sha256,
            'web_domain': self.web_domain,
            'true_office_id': self.true_office_id,
            'office_strings': self.office_strings
        }
        return json.dumps(js, ensure_ascii=False)

    def get_learn_target(self):
        target = self.office_index.get_ml_office_id(self.true_office_id)
        if target is None:
            raise Exception("sha256 = {} , cannot get ml office id by office_id = {}".format(
                self.sha256, self.true_office_id))
        return target

    @staticmethod
    def build_from_web_reference(office_index, sha256, src_doc: TSourceDocument, web_ref: TWebReference,
                                 true_office_id):
        web_domain = office_index.get_web_domain_by_url(web_ref.url, web_ref._site_url)
        return TPredictionCase(
            office_index,
            sha256=sha256,
            web_domain=web_domain,
            true_office_id=true_office_id,
            office_strings=src_doc.office_strings
        )

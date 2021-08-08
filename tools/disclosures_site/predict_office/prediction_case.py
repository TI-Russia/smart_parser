import json


class TPredictionCase:
    def __init__(self, ml_model=None, sha256=None, web_domain=None, true_office_id=None, office_strings=None):
        self.ml_model = ml_model
        self.sha256 = sha256
        self.office_strings = office_strings
        self.web_domain = web_domain
        self.text = self.get_text_from_office_strings()

        self.true_office_id = true_office_id
        if self.true_office_id is not None:
            self.true_region_id = ml_model.office_index.get_office_region(self.true_office_id)
        else:
            self.true_region_id = None

    def get_text_from_office_strings(self):
        if self.office_strings is None or len(self.office_strings) == 0:
            return ""
        office_strings = json.loads(self.office_strings)
        text = ""
        title = office_strings['title']
        if title is not None and len(title) > 0:
             text += office_strings['title'] + " "
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
        self.true_region_id = self.ml_model.office_index.get_office_region(self.true_office_id)
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
        target = self.ml_model.office_index.get_ml_office_id(self.true_office_id)
        assert target is not None
        return target

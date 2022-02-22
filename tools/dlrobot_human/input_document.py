from common.urllib_parse_pro import TUrlUtf8Encode
import json

class TIntersectionStatus:
    both_found = "both_found"
    only_dlrobot = "only_dlrobot"
    only_human = "only_human"

    @staticmethod
    def all_intersection_statuses():
        return [TIntersectionStatus.only_dlrobot, TIntersectionStatus.only_human, TIntersectionStatus.both_found]


class TReferenceBase:
    def __init__(self, site_url: ''):
        self._site_url = site_url

    def get_site_url(self):
        return self._site_url

    def convert_to_utf8(self):
        self._site_url = TUrlUtf8Encode.convert_if_idna(self._site_url)


class TDeclaratorReference (TReferenceBase):
    def __init__(self, from_json=dict()):
        self._site_url = from_json.get('web_domain')
        self.office_id = from_json.get('office_id')
        self.income_year = from_json.get('income_year')
        self.document_id = from_json.get('document_id')
        self.document_file_id = from_json.get('document_file_id')
        self.document_file_url = from_json.get('media_url')
        self.deleted_in_declarator_db = from_json.get('deleted_in_declarator_db')
        items_count = 6
        if self.deleted_in_declarator_db is not None:
            items_count += 1
        assert len(from_json) == 0 or len(from_json) == items_count

    def write_to_json(self):
        s = {
            'web_domain': self._site_url,
            'office_id': self.office_id,
            'income_year': self.income_year,
            'document_id': self.document_id,
            'document_file_id': self.document_file_id,
            'media_url': self.document_file_url,
        }
        if self.deleted_in_declarator_db is not None:
            s["deleted_in_declarator_db"] = True
        return s

    def __eq__(self, other):
        return self.document_file_id == other.document_file_id


class TWebReference (TReferenceBase):
    def __init__(self, from_json=dict(), url=None, crawl_epoch=None, site_url=None, declaration_year=None):
        self.url = from_json.get('url', url)
        self._site_url = from_json.get('web_domain', site_url)
        assert self._site_url is not None
        self.declaration_year = from_json.get('declaration_year', declaration_year)
        self.crawl_epoch = from_json.get('crawl_epoch', crawl_epoch)

    def write_to_json(self):
        rec = {
            'url': self.url,
            'crawl_epoch': self.crawl_epoch,
            'web_domain': self._site_url,
        }
        if self.declaration_year is not None:
            rec['declaration_year'] = self.declaration_year
        return rec

    def __eq__(self, other):
        return self.url == other.url and self.crawl_epoch == other.crawl_epoch


class TSourceDocument:

    def __init__(self, fiie_extension=None):
        self.file_extension = fiie_extension
        self.calculated_office_id = None
        self.web_references = list()
        self.decl_references = list()
        self.office_strings = None
        self.region_id = None

    def from_json(self, js):
        self.file_extension = js.get('file_ext')
        self.calculated_office_id = js.get('office_id')
        self.web_references = list(TWebReference(from_json=r) for r in js.get('w_refs', []))
        self.decl_references = list(TDeclaratorReference(from_json=r) for r in js.get('d_refs', []))
        self.office_strings = js.get('office_strings')
        self.region_id = js.get('region_id')
        return self

    def build_intersection_status(self):
        if len(self.web_references) > 0 and len(self.decl_references) > 0:
            return TIntersectionStatus.both_found
        elif len(self.web_references) > 0:
            return TIntersectionStatus.only_dlrobot
        elif len(self.decl_references) > 0:
            return TIntersectionStatus.only_human
        else:
            assert False

    def can_be_used_for_declarator_train(self):
        return self.build_intersection_status() == TIntersectionStatus.both_found

    def get_web_site(self):
        for r in self.decl_references:
            return r.get_site_url()
        for r in self.web_references:
            return r.get_site_url()
        return ""

    def get_declarator_income_year(self):
        for r in self.decl_references:
            if r.income_year is not None:
                return int(r.income_year)
        return None

    def get_external_income_year_from_dlrobot(self):
        for r in self.web_references:
            if r.declaration_year is not None:
                return int(r.declaration_year)
        return None

    def calc_document_income_year(self, smart_parser_json):
        # take income_year from the document heading
        year = smart_parser_json.get('document', dict()).get('year')

        # If absent, take it from declarator db
        if year is None:
            year = self.get_declarator_income_year()

        # If absent, take it from html anchor text
        if year is None:
            year = self.get_external_income_year_from_dlrobot()
        if year is None:
            return year
        return int(year)

    def add_web_reference(self, web_ref):
        if web_ref is not None and web_ref not in self.web_references:
            self.web_references.append(web_ref)

    def add_decl_reference(self, decl_ref):
        if decl_ref is not None and decl_ref not in self.decl_references:
            self.decl_references.append(decl_ref)

    def write_to_json(self):
        res = {
            'file_ext': self.file_extension,
            'office_id': self.calculated_office_id
        }
        if len(self.web_references) > 0:
            res['w_refs'] = list(x.write_to_json() for x in self.web_references)
        if len(self.decl_references) > 0:
            res['d_refs'] = list(x.write_to_json() for x in self.decl_references)
        if self.office_strings is not None:
            res['office_strings'] = self.office_strings
        if self.region_id is not None:
            res['region_id'] = self.region_id
        return res

    def convert_refs_to_utf8(self):
        ref: TReferenceBase
        for ref in self.decl_references:
            ref.convert_to_utf8()
        for ref in self.web_references:
            ref.convert_to_utf8()

    def get_doc_title(self):
        if self.office_strings is None:
            return ""
        return json.loads(self.office_strings).get('title', "")
from common.urllib_parse_pro import TUrlUtf8Encode

import os
import json
from collections import defaultdict
import dbm.gnu


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


class TDlrobotHumanFileDBM:

    def __init__(self, db_file_path):
        self.db_file_path = db_file_path
        self.access_mode = None
        self.db = None

    def sync_db(self):
        self.db.sync()

    def close_db(self):
        self.sync_db()
        self.db.close()
        self.db = None

    def convert_json_to_dbm(self):
        file_path, file_ext = os.path.splitext(self.db_file_path)
        json_path = self.db_file_path
        self.db_file_path = file_path + ".dbm"
        self.create_db()
        self.convert_from_json_fle(json_path)
        self.close_db()

    def _open(self, access_mode):
        file_path, file_ext = os.path.splitext(self.db_file_path)
        if file_ext == ".json":
            self.convert_json_to_dbm()
        _, file_ext = os.path.splitext(self.db_file_path)
        assert file_ext == ".dbm"
        self.access_mode = access_mode
        self.db = dbm.gnu.open(self.db_file_path, self.access_mode)

    def open_db_read_only(self):
        self._open("r")
        return self

    def open_write_mode(self):
        self._open("w")
        return self

    def create_db(self):
        if os.path.exists(self.db_file_path):
            os.unlink(self.db_file_path)
        self.access_mode = "cf"
        self.db = dbm.gnu.open(self.db_file_path, self.access_mode)
        return self

    def update_source_document(self, sha256, src_doc: TSourceDocument):
        assert self.access_mode != 'r'
        self.db[sha256] = json.dumps(src_doc.write_to_json(), ensure_ascii=False)

    def get_all_documents(self):
        k = self.db.firstkey()
        while k is not None:
            js = json.loads(self.db[k])
            sha256 = k.decode('latin')
            yield sha256, TSourceDocument().from_json(js)
            k = self.db.nextkey(k)

    def get_all_keys(self):
        k = self.db.firstkey()
        while k is not None:
            yield k.decode('latin')
            k = self.db.nextkey(k)

    def get_documents_count(self):
        return len(self.db)

    def get_document(self, sha256) -> TSourceDocument:
        return TSourceDocument().from_json(json.loads(self.db[sha256]))

    def get_document_maybe(self, sha256):
        s = self.db.get(sha256)
        if s is None:
            return s
        return TSourceDocument().from_json(json.loads(s))

    def convert_from_json_fle(self, json_path: str):
        with open(json_path) as inp:
            js = json.load(inp)
        for k, v in js['documents'].items():
            self.update_source_document(k, TSourceDocument().from_json(v))

    def to_json(self):
        documents = dict()
        for sha256, src_doc in self.get_all_documents():
            documents[sha256] = src_doc.write_to_json()
        return {
            "documents": documents
        }

    def get_stats(self):
        websites = set()
        files_count = 0
        both_found = 0
        only_dlrobot = 0
        only_human = 0
        extensions = defaultdict(int)
        crawl_epochs = defaultdict(int)

        for _, src_doc in self.get_all_documents():
            websites.add(src_doc.get_web_site())
            files_count += 1
            intersection_status = src_doc.build_intersection_status()
            if intersection_status == TIntersectionStatus.both_found:
                both_found += 1
            if intersection_status == TIntersectionStatus.only_dlrobot:
                only_dlrobot += 1
            if intersection_status == TIntersectionStatus.only_human:
                only_human += 1
            for ref in src_doc.web_references:
                crawl_epochs[ref.crawl_epoch] += 1
            extensions[src_doc.file_extension] += 1

        return {
            "web_sites_count": len(websites),
            "files_count": files_count,
            "both_found": both_found,
            "only_human": only_human,
            "only_dlrobot": only_dlrobot,
            "crawl_epochs": dict(crawl_epochs),
            "extensions": dict(extensions),
        }

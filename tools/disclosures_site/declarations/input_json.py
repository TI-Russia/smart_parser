import os
import json

from common.primitives import get_site_domain_wo_www
from collections import defaultdict


class TIntersectionStatus:
    both_found = "both_found"
    only_dlrobot = "only_dlrobot"
    only_human = "only_human"


class TDeclaratorReference:
    def __init__(self, from_json=dict()):
        self.web_domain = from_json.get('web_domain')
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
            'web_domain': self.web_domain,
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


class TWebReference:
    def __init__(self, from_json=dict(), url=None, crawl_epoch=None):
        self.url = from_json.get('url', url)
        self.crawl_epoch = from_json.get('crawl_epoch', crawl_epoch)
        assert len(from_json) == 0 or len(from_json) == 2

    def write_to_json(self):
        return {
            'url': self.url,
            'crawl_epoch': self.crawl_epoch
        }

    def __eq__(self, other):
        return self.url == other.url and self.crawl_epoch == other.crawl_epoch


class TSourceDocument:
    both_found = "both_found"
    only_dlrobot = "only_dlrobot"
    only_human = "only_human"

    def __init__(self, from_json=dict()):
        document_path = from_json.get('document_path')
        if document_path is not None:
            _, self.file_extension = os.path.splitext(document_path)   #old version
        else:
            self.file_extension = from_json.get('file_ext')
        self.calculated_office_id = from_json.get('office_id')
        self.web_references = list()
        self.decl_references = list()
        for ref in from_json.get('d_refs', []):
            self.decl_references.append(TDeclaratorReference(from_json=ref))
        for ref in from_json.get('w_refs', []):
            self.web_references.append(TWebReference(from_json=ref))

    def get_intersection_status(self):
        if len(self.web_references) > 0 and len(self.decl_references) > 0:
            return TSourceDocument.both_found
        elif len(self.web_references) > 0:
            return TSourceDocument.only_dlrobot
        elif len(self.decl_references) > 0:
            return TSourceDocument.only_human
        else:
            assert False

    def get_web_site(self):
        for r in self.decl_references:
            return r.web_domain
        for r in self.web_references:
            return get_site_domain_wo_www(r.url)
        return ""

    def get_declarator_income_year(self):
        for r in self.decl_references:
            if r.income_year is not None:
                return r.income_year
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
        return res


class TDlrobotHumanFile:
    def __init__(self, db_file_path, read_db=True, document_folder=None):
        self.db_file_path = db_file_path
        self.db_file_dirname = os.path.dirname(db_file_path)
        if read_db:
            with open(self.db_file_path, "r") as inp:
                from_json = json.load(inp)
            self.document_folder = from_json.get('document_folder')
            self.document_collection = dict(
                (k, TSourceDocument(from_json=v)) for k, v in from_json.get('documents', dict()).items())
        else:
            self.document_folder = document_folder
            self.document_collection = dict()
            if document_folder is not None:
                if not os.path.exists(document_folder):
                    os.mkdir(document_folder)

    def add_source_document(self, sha256, src_doc: TSourceDocument):
        self.document_collection[sha256] = src_doc

    def write(self):
        with open(self.db_file_path, "w", encoding="utf8") as out:
            output_json = {
                'document_folder': self.document_folder,
                'documents': dict((k, v.write_to_json()) for k,v in self.document_collection.items())
            }
            json.dump(output_json, out,  indent=4, sort_keys=True, ensure_ascii=False)

    def get_documents_count(self):
        return len(self.document_collection)

    def get_stats(self):
        websites = set()
        files_count = 0
        both_found = 0
        only_dlrobot = 0
        only_human = 0
        extensions = defaultdict(int)
        crawl_epochs = defaultdict(int)

        for src_doc in self.document_collection.values():
            websites.add(src_doc.get_web_site())
            files_count += 1
            intersection_status = src_doc.get_intersection_status()
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

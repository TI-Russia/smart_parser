import os
import json


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
        assert len(from_json) == 0 or len(from_json) == 6

    def write_to_json(self):
        return  {
            'web_domain': self.web_domain,
            'office_id': self.office_id,
            'income_year': self.income_year,
            'document_id': self.document_id,
            'document_file_id': self.document_file_id,
            'media_url': self.document_file_url,
        }

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
        self.document_path = from_json.get('document_path')
        self.intersection_status = from_json.get('intersection_status')
        self.calculated_office_id = from_json.get('office_id')
        self.web_references = list()
        self.decl_references = list()
        for ref in from_json.get('d_refs', []):
            self.decl_references.append(TDeclaratorReference(from_json=ref))
        for ref in from_json.get('w_refs', []):
            self.web_references.append(TWebReference(from_json=ref))

    def update_intersection_status(self, new_status):
        if self.intersection_status is None:
            self.intersection_status = new_status
        elif self.intersection_status != new_status:
            self.intersection_status = TSourceDocument.both_found

    def get_web_site(self):
        return os.path.dirname(self.document_path)

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
            'document_path': self.document_path,
            'intersection_status': self.intersection_status,
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

    def get_document_path(self, src_doc: TSourceDocument, absolute=False):
        if absolute:
            return os.path.join(self.db_file_dirname, self.document_folder, src_doc.document_path)
        else:
            return os.path.join(self.document_folder, src_doc.document_path)

    def write(self):
        with open(self.db_file_path, "w", encoding="utf8") as out:
            output_json = {
                'document_folder': self.document_folder,
                'documents': dict((k, v.write_to_json()) for k,v in self.document_collection.items())
            }
            json.dump(output_json, out,  indent=4, sort_keys=True, ensure_ascii=False)

    def get_all_offices(self):
        return set(x.calculated_office_id for x in self.document_collection.values() if x.calculated_office_id is not None)

    def get_documents_count(self):
        return len(self.document_collection)
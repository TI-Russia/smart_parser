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

    @staticmethod
    def check_json(j):
        return 'media_url' in j

    def write_to_json(self):
        return  {
            'web_domain': self.web_domain,
            'office_id': self.office_id,
            'income_year': self.income_year,
            'document_id': self.document_id,
            'document_file_id': self.document_file_id,
            'media_url': self.document_file_url,
        }


class TWebReference:
    def __init__(self, from_json=dict()):
        self.url = from_json.get('url')
        self.crawl_epoch = from_json.get('crawl_epoch')
        assert len(from_json) == 0 or len(from_json) == 2

    def write_to_json(self):
        return {
            'url': self.url,
            'crawl_epoch': self.crawl_epoch
        }


class TSourceDocument:
    both_found = "both_found"
    only_dlrobot = "only_dlrobot"
    only_human = "only_human"

    def __init__(self, from_json=dict()):
        self.document_path = from_json.get('document_path')
        self.intersection_status = from_json.get('intersection_status')
        self.calculated_office_id = from_json.get('office_id')
        self.references = list()
        for ref in from_json.get('refs', []):
            if TDeclaratorReference.check_json(ref):
                self.references.append(TDeclaratorReference(from_json=ref))
            else:
                self.references.append(TWebReference(from_json=ref))

    def get_web_site(self):
        return os.path.dirname(self.document_path)

    def get_declarator_income_year(self):
        for r in self.references:
            if isinstance(r, TDeclaratorReference):
                if r.income_year is not None:
                    return r.income_year
        return None

    def write_to_json(self):
        return {
            'document_path': self.document_path,
            'intersection_status': self.intersection_status,
            'office_id': self.calculated_office_id,
            'refs': list(x.write_to_json() for x in self.references)
        }


class TDlrobotHumanFile:
    def __init__(self, input_file_name=None):
        from_json = dict()
        self.input_file_name_dir_name = ""
        if input_file_name is not None:
            with open(input_file_name, "r") as inp:
                from_json = json.load(inp)
            self.input_file_name_dir_name = os.path.dirname(input_file_name)
        self.document_folder = from_json.get('document_folder')
        self.document_collection = dict((k, TSourceDocument(from_json=v)) for k, v in from_json.get('documents', dict()).items())

    def add_source_document(self, sha256, src_doc: TSourceDocument):
        self.document_collection[sha256] = src_doc

    def get_document_path(self, src_doc: TSourceDocument, absolute=False):
        if absolute:
            return os.path.join(self.input_file_name_dir_name, self.document_folder, src_doc.document_path)
        else:
            return os.path.join(self.document_folder, src_doc.document_path)

    def write(self, output_file_name):
        with open(output_file_name, "w", encoding="utf8") as out:
            output_json = {
                'document_folder': self.document_folder,
                'documents': dict((k, v.write_to_json()) for k,v in self.document_collection.items())
            }
            json.dump(output_json, out,  indent=4, sort_keys=True, ensure_ascii=False)

    def get_all_offices(self):
        return set(x.calculated_office_id for x in self.document_collection.values() if x.calculated_office_id is not None)


from dlrobot_human.input_document import TIntersectionStatus, TSourceDocument

import os
import json
from collections import defaultdict
import dbm.gnu


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

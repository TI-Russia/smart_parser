import dbm.gnu
import os
import threading
from collections import defaultdict
import declarations.models as models

class TPermaLinksDB:
    def __init__(self, filename, create=False):
        self.models = {models.Person, models.Section, models.Source_Document}
        if create:
            self.create_mode = True
            if os.path.exists(filename):
                os.unlink(filename)
            self.db = dbm.gnu.open(filename, "c")
            self.lock = None
            self.primary_keys = None
            for typ in self.models:
                self.save_records_count(typ, 0)
        else:
            self.db = dbm.gnu.open(filename)
            self.create_mode = False
            self.lock = threading.Lock()
            self.primary_keys = defaultdict(int)
            for typ in self.models:
                self.primary_keys[str(typ)] = int(self.db.get(str(typ)).decode('utf8'))

    def save_records_count(self, model_type, records_count):
        assert self.create_mode == True
        assert model_type in self.models
        self.db[str(model_type)] = str(records_count)

    def get_record_id(self, django_db_model):
        assert type(django_db_model) in self.models
        passport = django_db_model.permalink_passport()
        old_id = self.db.get(passport)
        if old_id is not None:
            return old_id
        with self.lock:
            record_id = self.primary_keys[str(type(django_db_model))]
            self.primary_keys[str(type(django_db_model))] += 1
        return record_id

    def put_record_id(self, django_db_model):
        self.db[django_db_model.permalink_passport()] = str(django_db_model.id)

    def close(self):
        self.db.close()
import dbm.gnu
import os
import declarations.models as models
from django.db import connection


class TPermaLinksDB:

    def __init__(self, filename):
        self.filename = filename
        self.models = {models.Person, models.Section, models.Source_Document}
        self.db = None

    def get_auto_increment_table_name(self, model):
        return model.objects.model._meta.db_table + "_auto_increment"

    def recreate_auto_increment_table(self, model):
        start_from = int(self.db.get(str(model)).decode('utf8'))
        auto_increment_table = self.get_auto_increment_table_name(model)
        with connection.cursor() as cursor:
            cursor.execute("drop table if exists {}".format(auto_increment_table))
            cursor.execute("create table {} (id int auto_increment, PRIMARY KEY (id))".format(auto_increment_table))
            cursor.execute("alter table {} auto_increment = {}".format(auto_increment_table, start_from))

    def close_db(self):
        self.db.close()
        self.db = None

    def open_db_read_only(self):
        self.db = dbm.gnu.open(self.filename)

    def create_sql_sequences(self):
        for model in self.models:
            self.recreate_auto_increment_table(model)

    def create_db(self):
        if os.path.exists(self.filename):
            os.unlink(self.filename)
        self.db = dbm.gnu.open(self.filename, "c")
        for typ in self.models:
            self.save_records_count(typ, 0)


    def save_records_count(self, model_type, records_count):
        assert model_type in self.models
        self.db[str(model_type)] = str(records_count)

    def get_record_id(self, django_db_model):
        assert type(django_db_model) in self.models
        passport = django_db_model.permalink_passport()
        old_id = self.db.get(passport)
        if old_id is not None:
            return old_id
        auto_increment_table = self.get_auto_increment_table_name(type(django_db_model))
        with connection.cursor() as cursor:
            cursor.execute("insert into {} (id) values (null);".format(auto_increment_table))
            record_id = cursor.lastrowid
        return record_id

    def put_record_id(self, django_db_model):
        self.db[django_db_model.permalink_passport()] = str(django_db_model.id)

    def close(self):
        self.db.close()
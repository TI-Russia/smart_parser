import declarations.models as models

import dbm.gnu
import os
from django.db import connection


class TPermaLinksDB:

    def __init__(self, filename):
        self.filename = filename
        self.models = {models.Person, models.Section, models.Source_Document}
        self.db = None
        self.access_mode = None

    @staticmethod
    def get_auto_increment_table_name(model):
        return model.objects.model._meta.db_table + "_auto_increment"

    # stores the next primary key value from the old database
    # this value is updated only in command create_permalinks_storage
    def save_max_plus_one_primary_key(self, model_type, next_value):
        assert model_type in self.models
        self.db[str(model_type)] = str(next_value)

    def get_max_plus_one_primary_key_from_the_old_db(self, model):
        return int(self.db.get(str(model)).decode('utf8'))

    def recreate_auto_increment_table(self, model):
        start_from = self.get_max_plus_one_primary_key_from_the_old_db(model)
        auto_increment_table = TPermaLinksDB.get_auto_increment_table_name(model)
        with connection.cursor() as cursor:
            cursor.execute("drop table if exists {}".format(auto_increment_table))
            cursor.execute("create table {} (id int auto_increment, PRIMARY KEY (id))".format(auto_increment_table))
            cursor.execute("alter table {} auto_increment = {}".format(auto_increment_table, start_from))

    def get_new_max_id(self, model):
        auto_increment_table = TPermaLinksDB.get_auto_increment_table_name(model)
        with connection.cursor() as cursor:
            cursor.execute("select max(id) from {};".format(auto_increment_table))
            for m, in cursor:
                if m is None:
                    return m
                else:
                    return int(m)

    def sync_db(self):
        self.db.sync()

    def _save_verification_code(self):
        self.db["verification_code"] = "1"

    def _check_verification_code(self):
        """ check the database is written completely by create_permalink_storage """
        assert self.db["verification_code"] == "1".encode('latin')

    def close_db(self):
        if self.access_mode == "cf":
            self._save_verification_code()
        self.sync_db()
        self.db.close()
        self.db = None

    def open_db_read_only(self):
        self.access_mode = "r"
        self.db = dbm.gnu.open(self.filename, self.access_mode)
        self._check_verification_code()

    def create_sql_sequences(self):
        for model in self.models:
            self.recreate_auto_increment_table(model)

    def create_db(self):
        if os.path.exists(self.filename):
            os.unlink(self.filename)
        self.access_mode = "cf"
        self.db = dbm.gnu.open(self.filename, self.access_mode)
        for typ in self.models:
            self.save_max_plus_one_primary_key(typ, 0)

    def get_record_id(self, django_db_model):
        assert type(django_db_model) in self.models
        for passport in django_db_model.permalink_passports():
            old_id = self.db.get(passport)
            if old_id is not None:
                return int(old_id)
        auto_increment_table = TPermaLinksDB.get_auto_increment_table_name(type(django_db_model))
        with connection.cursor() as cursor:
            cursor.execute("insert into {} (id) values (null);".format(auto_increment_table))
            record_id = cursor.lastrowid

        return int(record_id)

    def put_record_id(self, record):
        for passport in record.permalink_passports():
            self.db[passport] = str(record.id)

    def create_and_save_empty_db(self):
        self.create_db()
        self.create_sql_sequences()
        self._save_verification_code()
        self.close_db()

import dbm.gnu
import os
import declarations.models as models
from django.db import connection
import sys

class TPermaLinksDB:

    def __init__(self, filename):
        self.filename = filename
        self.models = {models.Person, models.Section, models.Source_Document}
        self.db = None

    def get_auto_increment_table_name(self, model):
        return model.objects.model._meta.db_table + "_auto_increment"

    def get_first_new_primary_key(self, model):
        return int(self.db.get(str(model)).decode('utf8'))

    def recreate_auto_increment_table(self, model):
        start_from = self.get_first_new_primary_key(model)
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
            self.save_next_primary_key_value(typ, 0)

    def save_next_primary_key_value(self, model_type, next_value):
        assert model_type in self.models
        self.db[str(model_type)] = str(next_value)

    def get_record_id(self, django_db_model):
        assert type(django_db_model) in self.models
        for passport in django_db_model.permalink_passports():
            old_id = self.db.get(passport)
            if old_id is not None:
                return int(old_id)
        auto_increment_table = self.get_auto_increment_table_name(type(django_db_model))
        with connection.cursor() as cursor:
            cursor.execute("insert into {} (id) values (null);".format(auto_increment_table))
            record_id = cursor.lastrowid
        return int(record_id)

    def put_record_id(self, django_db_model):
        for passport in django_db_model.permalink_passports():
            self.db[passport] = str(django_db_model.id)

    def close(self):
        self.db.close()


    def update_person_records_count_and_close(self):
        self.db = dbm.gnu.open(self.filename, "w")
        with connection.cursor() as cursor:
            cursor.execute("select max(id) m from declarations_person;")
            old_value = self.get_first_new_primary_key(models.Person)
            if old_value is None:
                old_value = 0                
            new_value = cursor.fetchone()[0]
            if new_value is None:
                new_value = 0                
            if new_value > old_value:
                sys.stderr.write("person old next primary key = {}, new one = {}\n".format(old_value, new_value))
                self.save_next_primary_key_value(models.Person, new_value)
            self.recreate_auto_increment_table(models.Person)
        self.close()
    
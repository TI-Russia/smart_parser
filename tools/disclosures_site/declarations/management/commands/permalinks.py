import declarations.models as models

import dbm.gnu
import os
from django.db import connection


class TPermaLinksDB:
    """  provides almost the same primary keys for sections, source_docs and persons to keep external web
     links stable """
    SECTION_PREFIX = "sc"
    PERSON_DECLARATOR_PREFIX = "psd"
    SOURCE_DOC_PREFIX = "sd"
    PERSON_PREFIX = "ps"

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
        return self

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

    def get_new_id(self, model_type):
        auto_increment_table = TPermaLinksDB.get_auto_increment_table_name(model_type)
        with connection.cursor() as cursor:
            cursor.execute("insert into {} (id) values (null);".format(auto_increment_table))
            record_id = cursor.lastrowid
        return int(record_id)

    #============ source doc ==================
    @staticmethod
    def get_source_doc_sha256_passport(sha256):
        return TPermaLinksDB.SOURCE_DOC_PREFIX + ";" + str(sha256)

    def save_source_doc(self, source_doc):
        self.db[TPermaLinksDB.get_source_doc_sha256_passport(source_doc.sha256)] = str(source_doc.id)

    def get_source_doc_id_by_sha256(self, sha256):
        passport = TPermaLinksDB.get_source_doc_sha256_passport(sha256)
        old_id = self.db.get(passport)
        if old_id is not None:
            return int(old_id)
        return self.get_new_id(models.Source_Document)

    #============  section ===============
    @staticmethod
    def get_section_passport(section):
        main_income = section.get_declarant_income_size()
        return "{};{};{};{};{}".format(
            TPermaLinksDB.SECTION_PREFIX,
            section.source_document.id,
            section.person_name.lower(),
            section.income_year, main_income)

    def get_person_id_by_section(self, section):
        passport = TPermaLinksDB.get_section_passport(section)
        section_info = self.db.get(passport)
        if section_info is not None:
            _, person_id = section_info.decode('utf8').split(';')
            if person_id == 'None':
                return None #a section that was not linked to a person in the previous db
            else:
                return int(person_id)
        else:
            return None  #a new section that did not exist in the previous db

    def get_section_id(self, section):
        passport = TPermaLinksDB.get_section_passport(section)
        section_info = self.db.get(passport)
        if section_info is not None:
            old_id, _ = section_info.decode('utf8').split(';')
            return int(old_id)
        return self.get_new_id(models.Section)

    def save_section(self, section):
        self.db[TPermaLinksDB.get_section_passport(section)] = "{};{}".format(section.id, section.person_id)

    #==========   person =============
    @staticmethod
    def get_person_declarator_passport(declarator_person_id):
        return TPermaLinksDB.PERSON_DECLARATOR_PREFIX + ";" + str(declarator_person_id)

    @staticmethod
    def get_person_id_passport(person_id):
        return TPermaLinksDB.PERSON_PREFIX + ";" + str(person_id)

    def save_person(self, person):
        self.db[TPermaLinksDB.get_person_declarator_passport(person.declarator_person_id)] = str(person.id)
        self.db[TPermaLinksDB.get_person_id_passport(person.id)] = str(len(person.section_set.all()))

    def get_section_count_by_person_id(self, person_id):
        passport = TPermaLinksDB.get_person_id_passport(person_id)
        section_count = self.db.get(passport)
        if section_count is not None:
            return int(section_count)

    def get_person_id_by_declarator_id(self, declarator_person_id):
        passport = TPermaLinksDB.get_person_declarator_passport(declarator_person_id)
        person_id = self.db.get(passport)
        if person_id is not None:
            return int(person_id)
        # новую персона,которая была сделана руками в деклараторе, - источнк изменения в пермалинках персон
        # поскольку мо могли сливать эту же персону под другим id
        return self.get_new_id(models.Person)


    def create_and_save_empty_db(self):
        self.create_db()
        self.create_sql_sequences()
        self._save_verification_code()
        self.close_db()

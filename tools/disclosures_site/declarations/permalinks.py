import django.db.models
import declarations.models as models
from declarations.section_passport import TSectionPassportItems

import dbm.gnu
import os
from django.db import connection


class TPermaLinksDB:
    """  provides almost the same primary keys for sections, source_docs and persons to keep external web
     links stable """

    def __init__(self, directory, model_type: django.db.models.Model):
        self.model_type = model_type
        self.filename = os.path.join(directory,  self.get_dbm_file_name())
        self.db = None
        self.access_mode = None

    def get_sql_table_name(self):
        return self.model_type.objects.model._meta.db_table

    def get_dbm_file_name(self):
        return "permalinks_{}.dbm".format(self.get_sql_table_name())

    def get_auto_increment_table_name(self):
        return self.get_sql_table_name() + "_auto_increment"

    # stores the next primary key value from the old database
    # this value is updated only in command create_permalinks_storage
    def save_max_plus_one_primary_key(self, next_value):
        self.db[self.get_sql_table_name()] = str(next_value)

    def get_max_plus_one_primary_key_from_the_old_db(self):
        return int(self.db.get(self.get_sql_table_name()).decode('utf8'))

    def recreate_auto_increment_table(self):
        start_from = self.get_max_plus_one_primary_key_from_the_old_db()
        auto_increment_table = self.get_auto_increment_table_name()
        with connection.cursor() as cursor:
            cursor.execute("drop table if exists {}".format(auto_increment_table))
            cursor.execute("create table {} (id int auto_increment, PRIMARY KEY (id))".format(auto_increment_table))
            cursor.execute("alter table {} auto_increment = {}".format(auto_increment_table, start_from))

    def get_last_inserted_id_for_testing(self):
        auto_increment_table = self.get_auto_increment_table_name()
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

    def create_db(self):
        if os.path.exists(self.filename):
            os.unlink(self.filename)
        self.access_mode = "cf"
        self.db = dbm.gnu.open(self.filename, self.access_mode)
        self.save_max_plus_one_primary_key(0)

    def _get_new_id(self):
        auto_increment_table = self.get_auto_increment_table_name()
        with connection.cursor() as cursor:
            cursor.execute("insert into {} (id) values (null);".format(auto_increment_table))
            record_id = cursor.lastrowid
        return int(record_id)

    def create_and_save_empty_db(self):
        self.create_db()
        self.recreate_auto_increment_table()
        self._save_verification_code()
        self.close_db()


class TPermaLinksSourceDocument(TPermaLinksDB):
    def __init__(self, directory):
        super().__init__(directory, models.Source_Document)

    @staticmethod
    def get_source_doc_sha256_passport(sha256):
        return str(sha256)

    def get_source_doc_id_by_sha256(self, sha256):
        passport = TPermaLinksSourceDocument.get_source_doc_sha256_passport(sha256)
        old_id = self.db.get(passport)
        if old_id is not None:
            return int(old_id), False
        return self._get_new_id(), True

    def save_source_doc(self, sha256, doc_id):
        self.db[TPermaLinksSourceDocument.get_source_doc_sha256_passport(sha256)] = str(doc_id)

    def save_dataset(self, logger):
        if models.Source_Document.objects.count() == 0:
            self.save_max_plus_one_primary_key(0)
        else:
            max_value = 0
            for record in models.Source_Document.objects.raw('select id, sha256 from declarations_source_document;'):
                self.save_source_doc(record.sha256, record.id)
                max_value = max(record.id, max_value)
            self.save_max_plus_one_primary_key(max_value + 1)


class TPermaLinksSection(TPermaLinksDB):
    def __init__(self, directory):
        super().__init__(directory, models.Section)

    def get_section_id(self, passport):
        section_id_str = self.db.get(passport)
        if section_id_str is not None:
            return int(section_id_str), False
        return self._get_new_id(), True

    def save_dataset(self, logger):
        if models.Section.objects.count() == 0:
            self.save_max_plus_one_primary_key(0)
        else:
            cnt = 0
            max_section_id = 0
            passport_factory = TSectionPassportItems.get_section_passport_components()
            for section_id, passport_items in passport_factory:
                cnt += 1
                if (cnt % 10000) == 0:
                    logger.debug("{}".format(cnt))
                passport = passport_items.get_main_section_passport()
                self.db[passport] = str(section_id)
                max_section_id = max(section_id, max_section_id)

            self.save_max_plus_one_primary_key(max_section_id + 1)


class TPermaLinksPerson(TPermaLinksDB):
    DECLARATOR_PREFIX = "d"
    SECTION_PREFIX = "s"

    def __init__(self, directory):
        super().__init__(directory, models.Person)

    @staticmethod
    def get_person_declarator_passport(declarator_person_id):
        return TPermaLinksPerson.DECLARATOR_PREFIX + ";" + str(declarator_person_id)

    @staticmethod
    def get_section_passport(section_id):
        return TPermaLinksPerson.SECTION_PREFIX + ";" + str(section_id)

    def get_person_id_by_section_id(self, section_id):
        person_id_str = self.db.get(TPermaLinksPerson.get_section_passport(section_id))
        if person_id_str is not None:
            return int(person_id_str)
        else:
            return None  #a new section that did not exist in the previous db

    def get_person_id_by_declarator_id(self, declarator_person_id):
        passport = TPermaLinksPerson.get_person_declarator_passport(declarator_person_id)
        person_id = self.db.get(passport)
        if person_id is not None:
            return int(person_id)
        # новая персона, которая была сделана руками в деклараторе, - это  источнк изменения в пермалинках персон
        # поскольку мы могли сливать эту же персону под другим id
        return self._get_new_id()

    def save_dataset(self, logger):
        if self.model_type.objects.count() == 0:
            self.save_max_plus_one_primary_key(0)
        else:
            logger.info("init section_id -> person_id")
            cnt = 0
            for section in models.Section.objects.raw("select id, person_id from declarations_section where person_id is not null"):
                cnt += 1
                if (cnt % 10000) == 0:
                    logger.debug("{}".format(cnt))
                self.db[TPermaLinksPerson.get_section_passport(section.id)] = str(section.person_id)

            logger.info("init person_id -> declarator_person_id")
            cnt = 0
            max_value = 0
            for person in models.Section.objects.raw("select id, declarator_person_id from declarations_person"):
                cnt += 1
                if (cnt % 10000) == 0:
                    logger.debug("{}".format(cnt))
                self.db[TPermaLinksPerson.get_person_declarator_passport(person.declarator_person_id)] = str(person.id)
                max_value = max(person.id, max_value)

            self.save_max_plus_one_primary_key(max_value + 1)


class TPermalinksManager:
    @staticmethod
    def add_arguments(self, parser):
        parser.add_argument(
                '--model',
            dest='model',
            help='model name: section, person or source_document, if no model specified, then build all models'
        )
        parser.add_argument(
                '--directory',
            dest='directory',
            default=".",
            help='directory to create in or to read dbm files from'
        )

    def __init__(self, logger, options):
        self.logger = logger
        self.dbs = list()
        directory = options.get("directory", ".")
        if options.get("model"):
            model_names = [options.get("model")]
        else:
            model_names = ["person", "section", "source_document"]

        for model in model_names:
            if model == "person":
                self.dbs.append(TPermaLinksPerson(directory))
            elif model == "section":
                self.dbs.append(TPermaLinksSection(directory))
            elif model == "source_document":
                self.dbs.append(TPermaLinksSourceDocument(directory))
            else:
                raise Exception("unknown model name: {}".format(model))

    def create_permalinks(self):
        for db in self.dbs:
            db.create_db()
            db.save_dataset(self.logger)
            db.close_db()

    def create_sql_sequences(self):
        for db in self.dbs:
            db.open_db_read_only()
            db.recreate_auto_increment_table()

    def create_empty_dbs(self):
        for db in self.dbs:
            db.create_and_save_empty_db()

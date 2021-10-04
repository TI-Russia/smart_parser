import django.db.models
import declarations.models as models
from declarations.section_passport import TSectionPassportItems1, TSectionPassportItems2

import dbm.gnu
import os
from django.db import connection


def get_max_sql_id(table_name):
    with connection.cursor() as cursor:
        cursor.execute("select max(id) from {};".format(table_name))
        for max_value, in cursor:
            return max_value


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
        if not os.path.exists(os.path.dirname(self.filename)):
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
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

    def get_old_source_doc_id_by_sha256(self, sha256):
        passport = TPermaLinksSourceDocument.get_source_doc_sha256_passport(sha256)
        doc_id = self.db.get(passport)
        if doc_id is None:
            return None
        return int(doc_id)

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
            sql = "select id, sha256 from declarations_source_document;"
            logger.info(sql)
            for record in models.Source_Document.objects.raw(sql):
                self.save_source_doc(record.sha256, record.id)
            self.save_max_plus_one_primary_key(get_max_sql_id("declarations_source_document") + 1)


class TPermaLinksSection(TPermaLinksDB):
    def __init__(self, directory):
        super().__init__(directory, models.Section)

    def get_section_id(self, passport1, passport2):
        section_id_str = self.db.get(passport1)
        if section_id_str is not None:
            return int(section_id_str), False

        section_id_str = self.db.get(passport2)
        if section_id_str is not None:
            return int(section_id_str), False
        return self._get_new_id(), True

    def use_section_passport_factory(self, logger, factory_type):
        logger.info("build section passport items ({})...".format(factory_type))
        passport_factory = factory_type.get_section_passport_components()
        cnt = 0
        logger.info("save section passport to db ({})...".format(factory_type))
        for section_id, passport_items in passport_factory:
            cnt += 1
            if (cnt % 100000) == 0:
                logger.debug("{}".format(cnt))
            passport = passport_items.get_main_section_passport()
            self.db[passport] = str(section_id)

    def save_dataset(self, logger):
        if models.Section.objects.count() == 0:
            self.save_max_plus_one_primary_key(0)
        else:
            self.use_section_passport_factory(logger, TSectionPassportItems1)
            self.use_section_passport_factory(logger, TSectionPassportItems2)
            self.save_max_plus_one_primary_key(get_max_sql_id("declarations_section") + 1)


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

    def get_person_id_by_declarator_id(self, declarator_person_id, section_id):
        passport = TPermaLinksPerson.get_person_declarator_passport(declarator_person_id)
        person_id = self.db.get(passport)
        if person_id is not None:
            # the previous disclosures.ru version  knows already this declarator_person_id
            return int(person_id)

        person_id = self.get_person_id_by_section_id(section_id)
        if person_id is not None:
            # declarator_person_id is new to disclosures, but the section section_id was already published by the
            # the previous disclosures.ru version, so we reuse this person_id
            # though this person_id was not connected to declarator or was connected to the other declarator_person_id
            return person_id

        # new section and new person_id
        return self._get_new_id()

    def save_dataset(self, logger):
        if self.model_type.objects.count() == 0:
            self.save_max_plus_one_primary_key(0)
        else:
            sql = "select id, person_id from declarations_section where person_id is not null"
            logger.info(sql)
            cnt = 0
            for section in models.Section.objects.raw(sql):
                cnt += 1
                if (cnt % 100000) == 0:
                    logger.debug("{}".format(cnt))
                self.db[TPermaLinksPerson.get_section_passport(section.id)] = str(section.person_id)

            sql = "select id, declarator_person_id from declarations_person where declarator_person_id is not null"
            logger.info(sql)
            cnt = 0
            for person in models.Person.objects.raw(sql):
                cnt += 1
                if (cnt % 100000) == 0:
                    logger.debug("{}".format(cnt))
                self.db[TPermaLinksPerson.get_person_declarator_passport(person.declarator_person_id)] = str(person.id)

            self.save_max_plus_one_primary_key(get_max_sql_id("declarations_person") + 1)


class TPermalinksManager:
    @staticmethod
    def add_arguments(parser):
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

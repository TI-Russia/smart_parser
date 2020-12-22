import declarations.models as models
from declarations.documents import stop_elastic_indexing
from django.core.management import BaseCommand
from common.primitives import queryset_iterator
from declarations.management.commands.permalinks import TPermaLinksDB
from declarations.russian_fio import TRussianFio

import logging
import pymysql
import os
import json


def setup_logging(logfilename="copy_person.log"):
    logger = logging.getLogger("copy_person")
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def build_section_passport(document_id, fio, income_main):
    if income_main is None:
        income_main = 0
    return "{}_{}_{}".format(document_id, fio.lower(), int(income_main))


def get_all_section_from_declarator_with_person_id(declarator_host):
    # query to declarator db
    if declarator_host is None:
        db_connection = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                        unix_socket="/var/run/mysqld/mysqld.sock")
    else:
        db_connection = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                        host=declarator_host)
    in_cursor = db_connection.cursor()
    in_cursor.execute("""
                    select  s.person_id,
                            d.id, 
                            floor(i.size),
                            s.original_fio, 
                            CONCAT(p.family_name, " ", p.name, " ", p.patronymic)
                    from declarations_section s
                    inner join declarations_person p on p.id = s.person_id
                    inner join declarations_document d on s.document_id = d.id
                    left join declarations_income i on i.section_id = s.id
                    where s.person_id is not null
                          and i.relative_id is null
                          and s.dedupe_score = 0;

    """)
    props_to_person_id = dict()
    for person_id, document_id, income_main, original_fio, person_fio in in_cursor:
        fio = original_fio
        if fio is None:
            fio = person_fio
        key1 = build_section_passport(document_id, fio, income_main)
        if key1 in props_to_person_id:
            props_to_person_id[key1] = "AMBIGUOUS_KEY"
        else:
            props_to_person_id[key1] = person_id

        fio = TRussianFio(fio)
        if fio.is_resolved:
            key2 = build_section_passport(document_id, fio.family_name, income_main)
            if key2 in props_to_person_id:
                props_to_person_id[key2] = "AMBIGUOUS_KEY"
            else:
                props_to_person_id[key2] = person_id

    return props_to_person_id


class Command(BaseCommand):
    help = 'copy person id from declarator to disclosures'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None
        self.primary_keys_builder = None
        self.logger = None
        self.declarator_person_id_to_disclosures_person_id = dict()

    def add_arguments(self, parser):
        parser.add_argument(
                '--read-person-from-json',
            dest='read_person_from_json',
            default=None,
            help='read person info  from json for testing'
        )
        parser.add_argument(
            '--permanent-links-db',
            dest='permanent_links_db',
            required=True
        )
        parser.add_argument(
            '--declarator-host',
            dest='declarator_host',
            required=False
        )
        parser.add_argument(
            '--person-name-prefix',
            dest='person_name_prefix',
            required=False
        )

    def open_permalinks_db(self):
        self.primary_keys_builder = TPermaLinksDB(self.options['permanent_links_db'])
        self.primary_keys_builder.open_db_read_only()

    def update_primary_keys(self):
        self.primary_keys_builder.close_db()
        self.primary_keys_builder.update_person_records_count_and_close()

    def build_passport_to_person_id_mapping_from_declarator(self):
        if self.options.get('read_person_from_json') is not None:
            with open(self.options.get('read_person_from_json'), "r", encoding="utf8") as inpf:
                return json.load(inpf)
        else:
            return get_all_section_from_declarator_with_person_id(self.options['declarator_host'])

    def copy_human_merge(self, section, declarator_person_id):
        person_id = self.declarator_person_id_to_disclosures_person_id.get(declarator_person_id)
        if person_id is None:
            # we think that person ids in declarator db are stable
            person = models.Person(declarator_person_id=declarator_person_id)
            person.id = self.primary_keys_builder.get_record_id(person)
            if person.person_name is None or len(person.person_name) < len(section.person_name):
                person.person_name = section.person_name
            person.save()
            self.declarator_person_id_to_disclosures_person_id[declarator_person_id] = person.id
        else:
            person = models.Person.objects.get(id=person_id)
            assert person is not None
            if person.person_name is None or len(person.person_name) < len(section.person_name):
                person.person_name = section.person_name
                person.save()

        self.logger.debug("connect section {} to person {}, declarator_person_id={}".format(
            section.id, person.id, declarator_person_id))

        section.person = person
        section.dedupe_score = None
        section.save()

    def process_section(self, section, section_passports):
        main_income = 0
        for i in section.income_set.all():
            if i.relative == models.Relative.main_declarant_code:
                main_income = i.size
        found_results = list()
        for declaration_info in section.source_document.declarator_file_reference_set.all():
            key1 = build_section_passport(declaration_info.declarator_document_id, section.person_name, main_income)
            found_res1 = section_passports.get(key1)
            if found_res1 is not None:
                found_results.append(found_res1)
            fio = TRussianFio(section.person_name)
            if fio.is_resolved:
                key2 = build_section_passport(declaration_info.declarator_document_id, fio.family_name, main_income)
                found_res2 = section_passports.get(key2)
                if found_res2 is not None:
                    found_results.append(found_res2)
            else:
                self.logger.error(
                    "section {} fio={} cannot find surname".format(section.id, section.person_name))

        if len(found_results) == 0:
            self.logger.debug("section {} fio={} cannot be found in declarator".format(section.id, section.person_name))
        else:
            for person_id  in found_results:
                if person_id != "AMBIGUOUS_KEY":
                    self.copy_human_merge(section, person_id)
                    return True
            self.logger.debug("section {} fio={} is ambiguous".format(section.id, section.person_name))
        return False

    def handle(self, *args, **options):
        self.logger = setup_logging()
        self.options = options
        self.open_permalinks_db()
        section_passports = self.build_passport_to_person_id_mapping_from_declarator()
        self.logger.info("found {} merges in declarator".format(len(section_passports)))
        self.logger.info("stop_elastic_indexing")
        stop_elastic_indexing()
        cnt = 0
        merge_count = 0
        sections = models.Section.objects
        if options.get('person_name_prefix') is not None:
            sections = sections.filter(person_name__startswith=options['person_name_prefix'])
        for section in queryset_iterator(sections):
            cnt += 1
            if (cnt % 10000) == 0:
                self.logger.debug("number processed sections = {}".format(cnt))
            if self.process_section(section, section_passports):
                merge_count += 1

        self.logger.info("set human person id to {} records".format(merge_count))
        self.update_primary_keys()
        self.logger.info("all done")

CopyPersonIdCommand=Command

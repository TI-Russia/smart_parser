import declarations.models as models
from django.core.management import BaseCommand
from declarations.permalinks import TPermaLinksPerson
from common.russian_fio import TRussianFio
from common.logging_wrapper import setup_logging

import pymysql
import json
from django.db import connection


def build_section_passport(document_id, fio, income_main):
    if income_main is None:
        income_main = 0
    return "{}_{}_{}".format(document_id, fio.lower(), int(income_main))


def get_all_section_from_declarator_with_person_id(declarator_host):
    # запрос в Декларатор, поиск секций, которые руками (s.dedupe_score = 0) привязаны к персонам
    if declarator_host is None:
        db_connection = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                        unix_socket="/var/run/mysqld/mysqld.sock")
    else:
        db_connection = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                        host=declarator_host)
    in_cursor = db_connection.cursor()
    # disable declarator persons after 2021-01-18 because Andre Jvirblis decided add person records without
    # dedupplication (see telegram)
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
                          and s.dedupe_score = 0
                          and (p.created_when is null or DATE(p.created_when) < '2021-01-18')
                          and person_id in (
                                    select person_id 
                                    from declarations_section 
                                    where person_id is not null 
                                    group by person_id 
                                    having count(*) > 1)
                    ;

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
        self.permalinks_db = None
        self.logger = None
        self.declarator_person_id_to_disclosures_person = dict()
        self.disclosures_person_id_to_disclosures_person = dict()

    def add_arguments(self, parser):
        parser.add_argument(
                '--read-person-from-json',
            dest='read_person_from_json',
            default=None,
            help='read person info  from json for testing'
        )
        parser.add_argument(
            '--permalinks-folder',
            dest='permalinks_folder',
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
        self.permalinks_db = TPermaLinksPerson(self.options['permalinks_folder'])
        self.permalinks_db.open_db_read_only()

    def build_passport_to_person_id_mapping_from_declarator(self):
        if self.options.get('read_person_from_json') is not None:
            with open(self.options.get('read_person_from_json'), "r", encoding="utf8") as inpf:
                return json.load(inpf)
        else:
            return get_all_section_from_declarator_with_person_id(self.options['declarator_host'])

    # we think that person ids in declarator db are stable
    def copy_human_merge(self, section, declarator_person_id):
        person = self.declarator_person_id_to_disclosures_person.get(declarator_person_id)
        if person is None:
            person_id = self.permalinks_db.get_person_id_by_declarator_id(declarator_person_id, section.id)
            if person_id in self.disclosures_person_id_to_disclosures_person:
                person = self.disclosures_person_id_to_disclosures_person.get(person_id)
                if  declarator_person_id != person.declarator_person_id:
                    self.logger.error("Person id={} has conflict declarator_person_id ({} != {}), use the first person id {}".format(
                        person_id, declarator_person_id, person.declarator_person_id, person.declarator_person_id))

            else:
                person = models.Person(
                    id=person_id,
                    declarator_person_id=declarator_person_id,
                    person_name=section.person_name)
                person.save()
                self.declarator_person_id_to_disclosures_person[declarator_person_id] = person
                self.disclosures_person_id_to_disclosures_person[declarator_person_id] = person
        elif person.person_name is None or len(person.person_name) < len(section.person_name):
            person.person_name = section.person_name
            person.save()

        assert person.declarator_person_id is not None
        self.logger.debug("connect section {} to person {}, declarator_person_id={}".format(
            section.id, person.id, person.declarator_person_id))

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

    def copy_declarator_person_ids(self, section_passports):
        query = """
            select s.id, r.declarator_document_id, s.person_name, i.size
            from declarations_section s
            join declarations_income i on i.section_id = s.id
            join declarations_source_document d on s.source_document_id = d.id
            join declarations_declarator_file_reference r on r.source_document_id = d.id
            where i.relative = '{}'
        """.format(models.Relative.main_declarant_code)
        merge_count = 0
        with connection.cursor() as cursor:
            cursor.execute(query)
            for section_id, declarator_document_id, person_name, main_income in cursor:
                found_results = list()
                key1 = build_section_passport(declarator_document_id, person_name, main_income)
                found_res1 = section_passports.get(key1)
                if found_res1 is not None:
                    found_results.append(found_res1)
                fio = TRussianFio(person_name)
                if fio.is_resolved:
                    key2 = build_section_passport(declarator_document_id, fio.family_name, main_income)
                    found_res2 = section_passports.get(key2)
                    if found_res2 is not None:
                        found_results.append(found_res2)
                if len(found_results) > 0:
                    success = False
                    for person_id in found_results:
                        if person_id != "AMBIGUOUS_KEY":
                            self.copy_human_merge(models.Section.objects.get(id=section_id), person_id)
                            success = True
                            merge_count += 1
                            break
                    if not success:
                        self.logger.debug("section {} fio={} is ambiguous".format(section_id, person_name))
        self.logger.info("set human person id to {} records".format(merge_count))

    def handle(self, *args, **options):
        self.logger = setup_logging(logger_name="copy_person")
        self.options = options
        self.logger.debug("models.Person.objects.count()={}".format(models.Person.objects.count()))
        assert models.Person.objects.count() == 0
        self.open_permalinks_db()
        section_passports = self.build_passport_to_person_id_mapping_from_declarator()
        self.logger.info("merge by {} passports from declarator".format(len(section_passports)))
        self.copy_declarator_person_ids(section_passports)
        self.permalinks_db.close_db()
        self.logger.info("all done")

CopyPersonIdCommand=Command

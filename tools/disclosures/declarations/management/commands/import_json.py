from django.core.management import BaseCommand
from multiprocessing import Pool
from django.db import connection
from collections import defaultdict
import declarations.models as models
from functools import partial
import pymysql
import os
import re
import sys
import json
import traceback
from declarations.countries import get_country_code
from django.db import transaction


def normalize_whitespace(str):
    str = re.sub(r'\s+', ' ', str)
    str = str.strip()
    return str


def get_document_file_id(file_info):
    file_id = os.path.splitext(os.path.basename(file_info['filepath']))[0]
    if file_id.find('_') != -1:
        file_id = file_id[0:file_id.find('_')]
    return int(file_id)


def get_smart_parser_results(input_path):
    if not os.path.exists(input_path):
        # todo: why ?
        print("Error! cannot find {}, though it is in dlrobot_human.json".format(input_path))
        return

    if os.path.exists(input_path + ".json"):
        yield input_path + ".json"
    else:
        index = 0
        while True:
            filename = input_path + "_{}.json".format(index)
            if not os.path.exists(filename):
                break
            yield filename
            index += 1


def build_stable_section_id_1(fio, income, year, office_id):
    fio = normalize_whitespace(fio).lower()
    if income is None:
        income = 0
    if year is None:
        year = 0
    return "\t".join([fio, str(int(income)), str(year), str(office_id)])


def build_stable_section_id_2(fio, income, year, office_id):
    fio = normalize_whitespace(fio).lower()
    if len(fio) > 0:
        fio = fio.split(" ")[0]  # only family_name
    if income is None:
        income = 0
    if year is None:
        year = 0
    return "\t".join([fio, str(int(income)), str(year), str(office_id)])


def init_person_info(section, section_json):
    person_info = section_json.get('person')
    if person_info is None:
        return False
    fio = person_info.get('name', person_info.get('name_raw'))
    if fio is None:
        return False
    section.person_name =  normalize_whitespace(fio.replace('"', ' '))
    section.person_name_ru = section.person_name
    section.position =  person_info.get("role")
    section.position_ru = section.position
    section.department =  person_info.get("department")
    section.department_ru = section.department
    return True


def create_section_incomes(section, section_json):
    for i in section_json.get('incomes', []):
        size = i.get('size')
        if isinstance(size, float) or (isinstance(size, str) and size.isdigit()):
            size = int(size)
        yield models.Income(section=section,
                          size=size,
                          relative=models.Relative.get_relative_code(i.get('relative'))
                          )


def create_section_real_estates(section, section_json):
    for i in section_json.get('real_estates', []):
        own_type_str = i.get("own_type", i.get("own_type_by_column"))
        country_str = i.get("country", i.get("country_raw"))
        yield models.RealEstate(
            section=section,
            type=i.get("type", i.get("text")),
            country=get_country_code(country_str),
            relative=models.Relative.get_relative_code(i.get('relative')),
            owntype=models.OwnType.get_own_type_code(own_type_str),
            square=i.get("square"),
            share=i.get("share_amount")
        )


def create_section_vehicles(section, section_json):
    for i in section_json.get('vehicles', []):
        text = i.get("text")
        if text is not None:
            yield models.Vehicle(
                section=section,
                name=text,
                name_ru=text,
                relative=models.Relative.get_relative_code( i.get('relative'))
            )


def register_source_file(file_path, office_id, source_file_sha256, web_domain):
    office = models.Office(id=office_id)
    docfile = models.DocumentFile(office=office, sha256=source_file_sha256, file_path=file_path, web_domain=web_domain)
    docfile.save()
    return docfile


def import_one_section( income_year, document_file, section_json):
    section = models.Section(
        document_file=document_file,
        income_year=income_year,
    )
    if not init_person_info(section, section_json):
        return
    section.save()
    try:
        models.Income.objects.bulk_create(create_section_incomes(section, section_json))
        models.RealEstate.objects.bulk_create(create_section_real_estates(section, section_json))
        models.Vehicle.objects.bulk_create(create_section_vehicles(section, section_json))
    except Exception as exp:
        print ("exception on {}: {}".format(section.person_name, exp))
        traceback.print_exc(file=sys.stdout)
        raise


class TDlrobotAndDeclarator:

    def init_file_2_documents(self):
        db_connection = TDlrobotAndDeclarator.get_declarator_db_connection()
        in_cursor = db_connection.cursor()
        in_cursor.execute("select id, document_id from declarations_documentfile")
        self.file_2_document = dict(x for x in in_cursor)
        for file_id, document_id in self.file_2_document.items():
            self.document_2_files[document_id].add(file_id)
        db_connection.close()


    def get_mapping_section_to_stable_id(self):
        db_connection = TDlrobotAndDeclarator.get_declarator_db_connection()
        in_cursor = db_connection.cursor()
        in_cursor.execute("""
                        select  s.id, 
                                s.person_id, 
                                d.office_id, 
                                i.size,
                                s.original_fio, 
                                CONCAT(p.family_name, " ", p.name, " ", p.patronymic),
                                d.income_year
                        from declarations_section s
                        inner join declarations_person p on p.id = s.person_id
                        inner join declarations_document d on s.document_id = d.id
                        inner join declarations_income i on i.section_id = s.id and i.relative_id is null
                        where s.person_id is not null
        """)

        human_persons = dict()
        human_section_mergings_count = 0
        for section_id, person_id, office_id, income, original_fio, person_fio, year in in_cursor:
            fio = original_fio
            if fio is None:
                fio = person_fio
            assert fio is not None
            key1 = build_stable_section_id_1(fio, income, year, office_id)
            if key1 not in human_persons:
                human_persons[key1] = person_id
            else:
                human_persons[key1] = None # if key is ambigous do not use it

            key2 = build_stable_section_id_2(fio, income, year, office_id)
            if key2 not in human_persons:
                human_persons[key2] = person_id
            else:
                human_persons[key2] = None # if key is ambigous do not use it
            human_section_mergings_count += 1

        in_cursor.close()
        db_connection.close()
        print("found {} sections with some person_id != null in declarator db".format(human_section_mergings_count))
        return human_persons

    def _copy_human_merges(self, human_persons):
        mergings_count = 0
        sys.stdout.write("set person_id to sections\n")

        with connection.cursor() as cursor:
            #pure django is 10x times slower
            cursor.execute(
                """
                    select s.id, s.income_year, s.person_name_ru, i.size, d.office_id 
                    from {} s
                    inner join {} d on s.document_file_id=d.id
                    inner join {} i on s.id=i.section_id and i.relative="{}" 
                """.format(
                        models.Section.objects.model._meta.db_table,
                        models.DocumentFile.objects.model._meta.db_table,
                        models.Income.objects.model._meta.db_table,
                        models.Relative.main_declarant_code)
            )
            cnt = 0
            for section_id, income_year, fio,  declarant_income, office_id in cursor.fetchall():
                cnt += 1
                if (cnt % 10000) == 0:
                    sys.stdout.write(".")
                key1 = build_stable_section_id_1(fio, declarant_income, income_year, office_id)
                key2 = build_stable_section_id_2(fio, declarant_income, income_year, office_id)
                person_id = human_persons.get(key1)
                if person_id is None:
                    person_id = human_persons.get(key2)

                if person_id is not None:
                    person = models.Person.objects.get_or_create(id=person_id)[0]
                    section = models.Section.objects.get(id=section_id)
                    section.person = person
                    section.save()
                    mergings_count += 1

        sys.stdout.write("\nset human person id to {} records\n".format(mergings_count))

    def copy_human_section_merges(self):
        human_persons = self.get_mapping_section_to_stable_id()
        self._copy_human_merges(human_persons)

    @staticmethod
    def get_declarator_db_connection():
        return pymysql.connect(db="declarator", user="declarator", password="declarator",
                                                        unix_socket="/var/run/mysqld/mysqld.sock")

    def build_office_domains(self):
        offices_to_domains = defaultdict(list)
        for domain in self.dlrobot_human_file_info:
            offices = list(x['office_id'] for x in self.dlrobot_human_file_info[domain].values() if 'office_id' in x)
            if len(offices) == 0:
                raise Exception("no office found for domain {}".format(domain))
            most_freq_office = max(set(offices), key=offices.count)
            offices_to_domains[most_freq_office].append(domain)
        return offices_to_domains

    def __init__(self, args):
        self.args = args
        self.file_2_document = dict()
        self.document_2_files = defaultdict(set)
        self.init_file_2_documents()
        with open(args['dlrobot_human'], "r", encoding="utf8") as inp:
            self.dlrobot_human_file_info = json.load(inp)
        self.office_to_domains = self.build_office_domains()

    def get_human_smart_parser_json(self, failed_files):
        documents = set()
        for file_id in failed_files:
            document_id = self.file_2_document.get(file_id)
            if document_id is None:
                print("cannot find file {}".format(file_id))
            else:
                documents.add(document_id)

        for document_id in documents:
            all_doc_files = self.document_2_files[document_id]
            if len(all_doc_files & failed_files) == len(all_doc_files):
                filename = os.path.join(self.args['smart_parser_human_json'], str(document_id) + ".json")
                if os.path.exists(filename):
                    print("import human file {}".format(filename))
                    yield filename, None, document_id

    @staticmethod
    def import_one_smart_parser_json(office_id, filepath, source_file_sha256, web_domain):
        docfile = register_source_file(filepath, office_id, source_file_sha256, web_domain)
        with open(filepath, "r", encoding="utf8") as inp:
            input_json = json.load(inp)
        income_year = input_json.get('document', dict()).get('year')
        if income_year is None:
            print ("cannot import {}, year is not defined".format(filepath))
            return
        income_year = int(income_year)
        section_count = 0
        with transaction.atomic():
            for p in input_json['persons']:
                import_one_section(income_year, docfile, p)
                section_count += 1
        print("import {} sections from {}".format(section_count, filepath))

    def import_office(self, office_id):
        for domain in self.office_to_domains[office_id]:
            print ("office {} domain {}".format(office_id, domain))
            jsons_to_import = list()

            failed_files = set()
            for source_file_sha256, file_info in self.dlrobot_human_file_info[domain].items():
                input_path = os.path.join("domains", domain, file_info['dlrobot_path'])
                smart_parser_results = list(get_smart_parser_results(input_path))
                if len(smart_parser_results) == 0:
                    if 'filepath' in file_info:
                        failed_files.add(get_document_file_id (file_info))
                else:
                    for file_path in smart_parser_results:
                        jsons_to_import.append( (file_path, source_file_sha256, None) )

            jsons_to_import += list(self.get_human_smart_parser_json(failed_files))

            for file_path, source_file_sha256, document_id in jsons_to_import:
                try:
                    TDlrobotAndDeclarator.import_one_smart_parser_json(office_id, file_path, source_file_sha256, domain)
                except Exception as exp:
                    print("Error! cannot import {}: {} ".format(file_path, exp))
                    traceback.print_exc(file=sys.stdout)


def process_one_file_in_thread(declarator_db, office_id):
    from django.db import connection
    connection.connect()
    try:
        declarator_db.import_office(office_id)
    except Exception as exp:
        print (exp)


class Command(BaseCommand):
    help = 'Import dlrobot and declarator files into disclosures db'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.importer = None
        self.options = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--process-count',
            dest='process_count',
            default=1,
            help='number of processes for import all'
        )
        parser.add_argument(
            '--dlrobot-human',
            dest='dlrobot_human',
            required=True
        )
        parser.add_argument(
            '--smart-parser-human-json-folder',
            dest='smart_parser_human_json',
            required=True
        )


    def handle(self, *args, **options):
        from django import db
        db.connections.close_all()

        declarator_db = TDlrobotAndDeclarator(options)

        pool = Pool(processes=int(options.get('process_count')))
        self.stdout.write("start importing")
        offices = list(i for i in declarator_db.office_to_domains.keys())
        pool.map(partial(process_one_file_in_thread, declarator_db), offices)
        declarator_db.copy_human_section_merges()

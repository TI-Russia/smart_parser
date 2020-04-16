from django.core.management import BaseCommand
from multiprocessing import Pool
from collections import defaultdict
import declarations.models as models
import pymysql
import os
import sys
from functools import partial
import json
from declarations.serializers import TSmartParserJsonReader
from django.db import transaction
from declarations.dlrobot_human_common import dhjs
from django.db import DatabaseError


def get_document_file_id(file_info):
    file_id = os.path.splitext(os.path.basename(file_info[dhjs.filepath]))[0]
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



class TSourceFile:
    def __init__(self, office_id, web_domain, file_sha256, file_info, declarator_documentfile_2_document):
        self.declarator_documentfile_id = None
        self.declarator_document_id = None
        if dhjs.filepath in file_info:
            self.declarator_documentfile_id = get_document_file_id(file_info)
            self.declarator_document_id = declarator_documentfile_2_document.get(self.declarator_documentfile_id)
        self.intersection_status = file_info[dhjs.intersection_status]
        self.office_id = office_id
        self.web_domain = web_domain
        self.file_sha256 = file_sha256


class TInputJsonFile:
    def __init__(self, source_file, json_file_path, intersection_status=None):
        self.source_file = source_file
        self.json_file_path = json_file_path
        self.intersection_status = intersection_status
        if self.intersection_status is None:
            self.intersection_status = source_file.intersection_status

    def get_import_priority(self):
        if self.source_file.intersection_status == dhjs.only_dlrobot:
            return 0 # import only_dlrobot last of all
        return 1

    def register_in_database(self):

        # mind that one source xlsx yields many source json files
        #if models.DocumentFile.objects.filter(sha256=self.source_file_sha256).first() is not None:
        #    raise TSmartParserJsonReader.SerializerException("source file with sha256={} already exists, skip importing!".format(source_file_sha256))

        office = models.Office(id=self.source_file.office_id)
        doc_file = models.SPJsonFile(office=office,
                                       sha256=self.source_file.file_sha256,
                                       file_path=self.json_file_path,
                                       web_domain=self.source_file.web_domain,
                                       intersection_status=self.intersection_status,
                                       declarator_documentfile_id=self.source_file.declarator_documentfile_id,
                                       declarator_document_id=self.source_file.declarator_document_id)
        doc_file.save()
        return doc_file



class TDlrobotAndDeclarator:

    def init_file_2_documents(self):
        db_connection = TDlrobotAndDeclarator.get_declarator_db_connection()
        in_cursor = db_connection.cursor()
        in_cursor.execute("""
            select f.id, f.document_id, d.income_year 
            from declarations_documentfile f 
            join declarations_document d on d.id = f.document_id
        """)
        for file_id, document_id, income_year in in_cursor:
            self.declarator_documentfile_2_document[file_id] = document_id
            self.document_2_files[document_id].add(file_id)
            self.declarator_document_2_income_year[document_id] = income_year
        db_connection.close()

    @staticmethod
    def get_declarator_db_connection():
        return pymysql.connect(db="declarator", user="declarator", password="declarator",
                                                        unix_socket="/var/run/mysqld/mysqld.sock")

    def build_office_domains(self):
        offices_to_domains = defaultdict(list)
        for domain in self.dlrobot_human_file_info:
            offices = list(x[dhjs.office_id] for x in self.dlrobot_human_file_info[domain].values() if dhjs.office_id in x)
            if len(offices) == 0:
                raise Exception("no office found for domain {}".format(domain))
            most_freq_office = max(set(offices), key=offices.count)
            offices_to_domains[most_freq_office].append(domain)
        return offices_to_domains

    def __init__(self, args):
        self.args = args
        self.declarator_documentfile_2_document = dict()
        self.document_2_files = defaultdict(set)
        self.declarator_document_2_income_year = dict()
        self.init_file_2_documents()
        with open(args['dlrobot_human'], "r", encoding="utf8") as inp:
            self.dlrobot_human_file_info = json.load(inp)
        self.office_to_domains = self.build_office_domains()
        self.all_section_passports = set()
        if models.Section.objects.count() > 0:
            raise Exception("implement all section passports reading from db if you want to import to non-empty db! ")

    def get_human_smart_parser_json(self, failed_files):
        # aggregate documentfile to documents
        documents = dict((source_file.declarator_document_id, source_file) for source_file in failed_files.values())

        for document_id, source_file in documents.items():
            all_doc_files = self.document_2_files[document_id]
            if len(all_doc_files & set(failed_files.keys())) == len(all_doc_files):  #if we failed to import all document files
                filename = os.path.join(self.args['smart_parser_human_json'], str(document_id) + ".json")
                if os.path.exists(filename):
                    print("import human file {}".format(filename))
                    yield TInputJsonFile(source_file, filename, dhjs.only_human)

    def register_section_passport(self, passport):
        if passport in self.all_section_passports:
            print("skip section because a section with the same passport already exists: {}".format(passport))
            return False
        # we process each office in one thread, so there  is no need to use thread.locks, since office_id is a part of passport tuple
        self.all_section_passports.add(passport)
        return True

    def import_one_smart_parser_json(self, json_file):
        filepath = json_file.json_file_path
        with open(filepath, "r", encoding="utf8") as inp:
            input_json = json.load(inp)
        income_year = input_json.get('document', dict()).get('year')
        if income_year is None and json_file.source_file.declarator_document_id is not None:
            # copy declarator income year
            income_year = self.declarator_document_2_income_year.get(json_file.source_file.declarator_document_id)
        if income_year is None:
            print ("cannot import {}, year is not defined".format(filepath))
            return
        income_year = int(income_year)

        docfile = json_file.register_in_database()
        imported_sections = 0
        section_index = 0
        for p in input_json['persons']:
            section_index += 1
            with transaction.atomic():
                try:
                    json_reader = TSmartParserJsonReader(income_year, docfile, p)
                    passport = json_reader.get_passport_factory().get_passport_collection()[0]
                    if self.register_section_passport(passport):
                        json_reader.save_to_database()
                        imported_sections += 1
                except (DatabaseError, TSmartParserJsonReader.SerializerException) as exp:
                    print("Error! cannot import section N {}: {} ".format(section_index, exp))
                    #traceback.print_exc(file=sys.stdout)
        if imported_sections == 0:
            print("no sections imported from {}".format(filepath))
            docfile.delete()
        else:
            print("import {} sections out of {} from {}".format(imported_sections, section_index, filepath))

    def import_office(self, office_id):
        for domain in self.office_to_domains[office_id]:
            print ("office {} domain {}".format(office_id, domain))
            jsons_to_import = list()

            failed_files = dict()
            for source_file_sha256, file_info in self.dlrobot_human_file_info[domain].items():
                file_office_id = file_info.get(dhjs.office_id, office_id)
                source_file = TSourceFile(file_office_id, domain, source_file_sha256, file_info, self.declarator_documentfile_2_document)
                input_path = os.path.join("domains", domain, file_info[dhjs.dlrobot_path])
                smart_parser_results = list(get_smart_parser_results(input_path))
                if len(smart_parser_results) == 0:
                    if source_file.declarator_document_id is not None:
                        failed_files[source_file.declarator_documentfile_id] = source_file
                else:
                    for file_path in smart_parser_results:  #xlsx sheets
                        jsons_to_import.append( TInputJsonFile(source_file, file_path) )

            jsons_to_import += list(self.get_human_smart_parser_json(failed_files))
            jsons_to_import.sort(key=(lambda x: x.get_import_priority()), reverse=True)
            for json_file in jsons_to_import:
                try:
                    self.import_one_smart_parser_json(json_file)
                except TSmartParserJsonReader.SerializerException as exp:
                    print("Error! cannot import {}: {} ".format(file_path, exp))
                    #traceback.print_exc(file=sys.stdout)


def process_one_file_in_thread(declarator_db, office_id):
    from django.db import connection
    connection.connect()
    try:
        declarator_db.import_office(office_id)
    except TSmartParserJsonReader.SerializerException as exp:
        print (exp)
        #traceback.print_exc(file=sys.stdout)


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

        #offices = offices[0:10]
        pool.map(partial(process_one_file_in_thread, declarator_db), offices)

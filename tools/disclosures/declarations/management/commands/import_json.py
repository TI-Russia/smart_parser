import declarations.models as models
from declarations.serializers import TSmartParserJsonReader
from declarations.input_json_specification import dhjs

from django.core.management import BaseCommand
from django.db import transaction
from django.db import DatabaseError

from multiprocessing import Pool
from collections import defaultdict
import os
from functools import partial
import json
import logging


def setup_logging(logfilename):
    logger = logging.getLogger("import_json")
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

    # create console handler with a higher log level
    #ch = logging.StreamHandler()
    #ch.setLevel(logging.DEBUG)
    #logger.addHandler(ch)
    return logger


def get_smart_parser_results(logger, input_path):
    if not os.path.exists(input_path):
        # todo: why ?
        logger.error("cannot find {}, though it is in dlrobot_human.json".format(input_path))
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


class TSourceDocumentFile:
    def __init__(self, office_id, web_domain, file_sha256, file_info):
        self.declarator_documentfile_id = file_info.get(dhjs.declarator_document_file_id)
        self.declarator_document_id = file_info.get(dhjs.declarator_document_id)
        self.declarator_income_year = file_info.get(dhjs.declarator_income_year)
        self.intersection_status = file_info[dhjs.intersection_status]
        self.office_id = office_id
        self.web_domain = web_domain
        self.file_sha256 = file_sha256

    def __hash__(self):
        return hash(self.file_sha256)


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

        # mind that one source xlsx yields many source json files, so no filtering by sha256 is possible

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


class TImporter:
    def init_document_2_files(self):
        document_2_files = defaultdict(set)
        for web_site_info in self.dlrobot_human_file_info.values():
            for file_info in web_site_info.values():
                document_id = file_info.get(dhjs.declarator_document_id)
                if document_id is not None:
                    document_2_files[document_id].add(file_info[dhjs.declarator_document_file_id])
        self.logger.debug("built {} document_2_files".format(len(document_2_files)))
        return document_2_files

    def build_office_domains(self):
        offices_to_domains = defaultdict(list)
        for web_domain in self.dlrobot_human_file_info:
            offices = list(x[dhjs.declarator_office_id] for x in self.dlrobot_human_file_info[web_domain].values() if dhjs.declarator_office_id in x)
            if len(offices) == 0:
                raise Exception("no office found for domain {}".format(domain))
            most_freq_office = max(set(offices), key=offices.count)
            offices_to_domains[most_freq_office].append(web_domain)
        self.logger.debug("built {} offices_to_domains".format(len(offices_to_domains)))
        return offices_to_domains

    def __init__(self, args):
        self.logger = setup_logging("import_json.log")
        self.args = args

        with open(args['dlrobot_human'], "r", encoding="utf8") as inp:
            dlrobot_human = json.load(inp)
            self.dlrobot_folder = dlrobot_human[dhjs.dlrobot_folder]
            if not os.path.isabs(self.dlrobot_folder):
                self.dlrobot_folder = os.path.join(os.path.dirname(args['dlrobot_human']), self.dlrobot_folder)
            self.dlrobot_human_file_info = dlrobot_human[dhjs.file_collection]
        self.logger.debug("load information about {} sites ".format(len(self.dlrobot_human_file_info)))
        self.document_2_files = self.init_document_2_files()
        self.office_to_domains = self.build_office_domains()
        self.all_section_passports = set()
        if models.Section.objects.count() > 0:
            raise Exception("implement all section passports reading from db if you want to import to non-empty db! ")

    def get_human_smart_parser_json(self, failed_documents):
        for document_id, source_files in failed_documents.items():
            all_doc_files = self.document_2_files[document_id]
            if len(source_files) >= len(all_doc_files):  #if smart_parser failed to parse all document files
                filename = os.path.join(self.args['smart_parser_human_json'], str(document_id) + ".json")
                if os.path.exists(filename):
                    self.logger.debug("import human json {}".format(filename))
                    yield TInputJsonFile(list(source_files)[0], filename, dhjs.only_human)

    def register_section_passport(self, passport):
        if passport in self.all_section_passports:
            self.logger.debug("skip section because a section with the same passport already exists: {}".format(passport))
            return False
        # we process each office in one thread, so there  is no need to use thread.locks, since office_id is a part of passport tuple
        self.all_section_passports.add(passport)
        return True

    def import_one_smart_parser_json(self, json_file):
        filepath = json_file.json_file_path
        with open(filepath, "r", encoding="utf8") as inp:
            input_json = json.load(inp)
        # take income_year from smart_parser. If absent, take it from declarator, otherwise the file is useless
        income_year = input_json.get('document', dict()).get('year', json_file.source_file.declarator_income_year)
        if income_year is None:
            self.logger.error("cannot import {}, year is not defined".format(filepath))
            return
        income_year = int(income_year)

        doc_file = json_file.register_in_database()
        imported_sections = 0
        section_index = 0
        for p in input_json['persons']:
            section_index += 1
            with transaction.atomic():
                try:
                    json_reader = TSmartParserJsonReader(income_year, doc_file, p)
                    passport = json_reader.get_passport_factory().get_passport_collection()[0]
                    if self.register_section_passport(passport):
                        json_reader.save_to_database()
                        imported_sections += 1
                except (DatabaseError, TSmartParserJsonReader.SerializerException) as exp:
                    self.logger.error("Error! cannot import section N {}: {} ".format(section_index, exp))
        if imported_sections == 0:
            self.logger.debug("no sections imported from {}".format(filepath))
            doc_file.delete()
        else:
            self.logger.debug("import {} sections out of {} from {}".format(imported_sections, section_index, filepath))

    def import_office(self, office_id):
        for web_site in self.office_to_domains[office_id]:
            self.logger.debug("office {} domain {}".format(office_id, web_site))
            jsons_to_import = list()

            failed_documents = defaultdict(set)
            for source_file_sha256, file_info in self.dlrobot_human_file_info[web_site].items():
                file_office_id = file_info.get(dhjs.declarator_office_id, office_id)
                source_file = TSourceDocumentFile(file_office_id, web_site, source_file_sha256, file_info)
                input_path = os.path.join(self.dlrobot_folder, web_site, file_info[dhjs.dlrobot_path])
                smart_parser_results = list(get_smart_parser_results(self.logger, input_path))
                if len(smart_parser_results) == 0:
                    if source_file.declarator_document_id is not None:
                        failed_documents[source_file.declarator_document_id].add(source_file)
                else:
                    for file_path in smart_parser_results:  #xlsx sheets
                        jsons_to_import.append(TInputJsonFile(source_file, file_path) )

            jsons_to_import += list(self.get_human_smart_parser_json(failed_documents))
            jsons_to_import.sort(key=(lambda x: x.get_import_priority()), reverse=True)
            for json_file in jsons_to_import:
                try:
                    self.import_one_smart_parser_json(json_file)
                except TSmartParserJsonReader.SerializerException as exp:
                    self.logger.error("Error! cannot import {}: {} ".format(file_path, exp))


def process_one_file_in_thread(importer: TImporter, office_id):
    from django.db import connection
    connection.connect()
    try:
        importer.import_office(office_id)
    except TSmartParserJsonReader.SerializerException as exp:
        importer.logger.error("cannot import office {}, exception: {}".format(office_id), exp)


class ImportJsonCommand(BaseCommand):
    help = 'Import dlrobot and declarator files into disclosures db'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

        importer = TImporter(options)

        offices = list(i for i in importer.office_to_domains.keys())
        self.stdout.write("start importing")

        if options.get('process_count', 0) > 1:
            from django import db
            db.connections.close_all()
            pool = Pool(processes=int(options.get('process_count')))
            pool.map(partial(process_one_file_in_thread, importer), offices)
        else:
            for office_id in offices:
                importer.import_office(office_id)

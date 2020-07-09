import declarations.models as models
from declarations.serializers import TSmartParserJsonReader
from declarations.documents import stop_elastic_indexing
from django.core.management import BaseCommand
from django.db import transaction
from django.db import DatabaseError

from multiprocessing import Pool
import os
from functools import partial
import json
import logging
from django_elasticsearch_dsl.management.commands.search_index import Command as ElasticManagement
from declarations.input_json import  TDeclaratorReference, TDlrobotHumanFile

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


def register_in_database(sha256, src_doc):
    office = models.Office(id=src_doc.calculated_office_id)
    source_document_in_db = models.Source_Document(office=office,
                                                        sha256=sha256,
                                                        file_path=src_doc.document_path,
                                                        intersection_status=src_doc.intersection_status,
                                                        )
    source_document_in_db.save()
    for ref im src_doc.references:
        if isinstance(ref, TDeclaratorReference):
            models.Declarator_File_Reference(source_document=source_document_in_db,
                                             declarator_documentfile_id=ref.document_file_id,
                                             declarator_document_id=ref.document_id,
                                             declarator_document_file_url=ref.document_file_url).save()
        else:
            models.Web_Reference(source_document=source_document_in_db,
                                 dlrobot_url=ref.url,
                                 crawl_epoch=ref.crawl_epoch).save()

    return source_document_in_db


class TImporter:
    logger = None

    def check_office_integrity(self, offices):
        db_offices = set()
        for o in models.Office.objects.all():
            db_offices.add(o.id)

        for office_id in offices:
            if int(office_id) not in db_offices:
                self.logger.error("cannot find office {} references in dlrobot_human.json ".format(office_id))
                raise Exception("integrity failed")

    def __init__(self, args):
        self.args = args
        self.dlrobot_human = TDlrobotHumanFile(input_file_name=args['dlrobot_human'])
        TImporter.logger.debug("load information about {} sites ".format(len(self.dlrobot_human_file_info)))
        self.all_section_passports = set()
        if models.Section.objects.count() > 0:
            raise Exception("implement all section passports reading from db if you want to import to non-empty db! ")

    def get_human_smart_parser_json(self, src_doc, already_imported):
        res = set()
        for ref in src_doc.referemces:
            if isinstance(ref, TDeclaratorReference):
                filename = os.path.join(self.args['smart_parser_human_json'], str(ref.document_id) + ".json")
                if os.path.exists(filename) and filename not in already_imported:
                    TImporter.logger.debug("import human json {}".format(filename))
                    already_imported.add(filename)
                    res.add(filename)
        return res

    def register_section_passport(self, passport):
        if passport in self.all_section_passports:
            TImporter.logger.debug("skip section because a section with the same passport already exists: {}".format(passport))
            return False
        # we process each office in one thread, so there  is no need to use thread.locks, since office_id is a part of passport tuple
        self.all_section_passports.add(passport)
        return True

    def import_one_smart_parser_json(self, source_document, filepath):
        with open(filepath, "r", encoding="utf8") as inp:
            input_json = json.load(inp)
        # take income_year from smart_parser. If absent, take it from declarator, otherwise the file is useless
        income_year = input_json.get('document', dict()).get('year', source_document.declarator_income_year)
        if income_year is None:
            TImporter.logger.error("cannot import {}, year is not defined".format(filepath))
            return
        income_year = int(income_year)

        imported_sections = 0
        section_index = 0
        for p in input_json['persons']:
            section_index += 1
            with transaction.atomic():
                try:
                    json_reader = TSmartParserJsonReader(income_year, source_document.source_document_in_db, p)
                    passport = json_reader.get_passport_factory().get_passport_collection()[0]
                    if self.register_section_passport(passport):
                        json_reader.save_to_database()
                        imported_sections += 1
                except (DatabaseError, TSmartParserJsonReader.SerializerException) as exp:
                    TImporter.logger.error("Error! cannot import section N {}: {} ".format(section_index, exp))
        if imported_sections == 0:
            TImporter.logger.debug("no sections imported from {}".format(filepath))
        else:
            TImporter.logger.debug("import {} sections out of {} from {}".format(imported_sections, section_index, filepath))

    def import_office(self, office_id):
        all_imported_human_jsons = set()
        for sha256, src_doc in self.dlrobot_human.document_collectio.items():
            if src_doc.calculated_office_id != office_id:
                continue
            input_path = self.dlrobot_human.get_document_path(src_doc, absolute=True)
            json_files = set(get_smart_parser_results(TImporter.logger, input_path))
            if len(json_files) == 0:
                json_files = self.get_human_smart_parser_json(src_doc, all_imported_human_jsons)

            doc_file_in_db = register_in_database(sha256, src_doc)
            for json_file in json_files:
                try:
                    self.import_one_smart_parser_json(doc_file_in_db, json_file)
                except TSmartParserJsonReader.SerializerException as exp:
                    TImporter.logger.error("Error! cannot import {}: {} ".format(json_file, exp))


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
            type=int,
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
        parser.add_argument(
            '--take-first-n-offices',
            dest='take_first_n_offices',
            required=False,
            type=int,
        )

    def handle(self, *args, **options):
        TImporter.logger = setup_logging("import_json.log")
        importer = TImporter(options)
        stop_elastic_indexing()
        offices = list(importer.dlrobot_human.get_all_offices())
        importer.check_office_integrity(offices)
        self.stdout.write("start importing")
        if options.get('process_count', 0) > 1:
            from django import db
            db.connections.close_all()
            pool = Pool(processes=options.get('process_count'))
            pool.map(partial(process_one_file_in_thread, importer), offices)
        else:
            cnt = 0
            for office_id in offices:
                if options.get('take_first_n_offices') is not None and cnt >= options.get('take_first_n_offices'):
                    break
                importer.import_office(office_id)
                cnt += 1
        importer.logger.info ("Section count={}".format(models.Section.objects.all().count()))
        ElasticManagement().handle(action="rebuild", models=["declarations.Section"], force=True, parallel=True, count=True)

Command=ImportJsonCommand
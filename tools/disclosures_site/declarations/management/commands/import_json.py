import declarations.models as models
from declarations.serializers import TSmartParserJsonReader
from declarations.documents import stop_elastic_indexing, start_elastic_indexing
from declarations.management.commands.permalinks import TPermaLinksDB
from smart_parser_http.smart_parser_client import TSmartParserCacheClient
from declarations.input_json import TDlrobotHumanFile
from declarations.rubrics import convert_municipality_to_education, TOfficeRubrics
from declarations.documents import OFFICES

from multiprocessing import Pool
import os
from functools import partial
import json
import logging
from collections import defaultdict
from django.core.management import BaseCommand
from django.db import transaction
from django.db import DatabaseError
import gc


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

    return logger


class TImporter:
    logger = None

    def build_office_to_file_mapping(self):
        db_offices = set(o.id for o in models.Office.objects.all())
        TImporter.logger.debug("there are {} records in table {} ".format(
            len(db_offices),
            models.Office.objects.model._meta.db_table))
        office_to_source_documents = defaultdict(list)
        for sha256, src_doc in self.dlrobot_human.document_collection.items():
            office_id = src_doc.calculated_office_id
            if office_id is None:
                continue
            if int(office_id) not in db_offices:
                TImporter.logger.error("cannot find office id={} from {} in sql table ".format(
                    office_id, self.args['dlrobot_human']))
                raise Exception("integrity failed")
            office_to_source_documents[office_id].append(sha256)
        return office_to_source_documents

    def __init__(self, args):
        self.args = args
        self.dlrobot_human = TDlrobotHumanFile(args['dlrobot_human'])
        self.all_section_passports = set()
        if models.Section.objects.count() > 0:
            raise Exception("implement all section passports reading from db if you want to import to non-empty db! ")
        self.office_to_source_documents = self.build_office_to_file_mapping()
        self.permalinks_db = TPermaLinksDB(args['permanent_links_db'])
        self.permalinks_db.open_db_read_only()
        self.first_new_section_id_for_print = self.permalinks_db.get_max_plus_one_primary_key_from_the_old_db(models.Section)
        self.smart_parser_cache_client = None

    def delete_before_fork(self):
        self.permalinks_db.close_db()
        from django import db
        db.connections.close_all()

    def init_non_pickable(self):
        self.smart_parser_cache_client = TSmartParserCacheClient(TSmartParserCacheClient.parse_args([]), TImporter.logger)
        self.permalinks_db.open_db_read_only()

    def init_after_fork(self):
        from django.db import connection
        connection.connect()
        self.init_non_pickable()

    def get_human_smart_parser_json(self, src_doc, already_imported):
        for ref in src_doc.decl_references:
            filename = os.path.join(self.args['smart_parser_human_json'], str(ref.document_id) + ".json")
            if os.path.exists(filename) and filename not in already_imported:
                TImporter.logger.debug("import human json {}".format(filename))
                already_imported.add(filename)
                with open (filename, "r") as inp:
                    return json.load(inp)
        return None

    def register_document_in_database(self, sha256, src_doc):
        office = models.Office(id=src_doc.calculated_office_id)
        source_document_in_db = models.Source_Document(office=office,
                                                       sha256=sha256,
                                                       intersection_status=src_doc.get_intersection_status(),
                                                       )
        source_document_in_db.id = self.permalinks_db.get_source_doc_id_by_sha256(sha256)
        source_document_in_db.file_extension = src_doc.file_extension
        source_document_in_db.save()
        for ref in src_doc.decl_references:
            models.Declarator_File_Reference(source_document=source_document_in_db,
                                             declarator_documentfile_id=ref.document_file_id,
                                             declarator_document_id=ref.document_id,
                                             web_domain=ref.web_domain,
                                             declarator_document_file_url=ref.document_file_url).save()
        for ref in src_doc.web_references:
            models.Web_Reference(source_document=source_document_in_db,
                                 dlrobot_url=ref.url,
                                 web_domain=ref.web_domain,
                                 crawl_epoch=ref.crawl_epoch).save()

        return source_document_in_db

    def register_section_passport(self, passport):
        if passport in self.all_section_passports:
            TImporter.logger.debug("skip section because a section with the same passport already exists: {}".format(passport))
            return False
        # we process each office in one thread, so there  is no need to use thread.locks, since office_id is a part of passport tuple
        self.all_section_passports.add(passport)
        return True

    def import_one_smart_parser_json(self, declarator_income_year, source_document_in_db, input_json):
        # take income_year from smart_parser. If absent, take it from declarator, otherwise the file is useless
        common_income_year = input_json.get('document', dict()).get('year', declarator_income_year)
        if common_income_year is not None:
            common_income_year = int(common_income_year)

        imported_section_years = list()
        section_index = 0
        TImporter.logger.debug("try to import {} declarants".format(len(input_json['persons'])))

        for p in input_json['persons']:
            section_index += 1
            income_year = p.get('year', common_income_year)
            if income_year is None:
                raise TSmartParserJsonReader.SerializerException("year is not defined: section No {}".format(section_index))
            with transaction.atomic():
                try:
                    json_reader = TSmartParserJsonReader(income_year, source_document_in_db, p)
                    passport = json_reader.get_passport_factory().get_passport_collection()[0]
                    if self.register_section_passport(passport):
                        json_reader.section.tmp_income_set = json_reader.incomes
                        section_id = self.permalinks_db.get_section_id(json_reader.section)
                        if section_id >= self.first_new_section_id_for_print:
                            TImporter.logger.debug("found a new section {}, set section.id to {}".format(
                                json_reader.section.get_permalink_passport(), section_id))

                        # json_reader.section.rubric_id = source_document_in_db.office.rubric_id does not work
                        # may be we should call source_document_in_db.refresh_from_db
                        json_reader.section.rubric_id = OFFICES.offices[source_document_in_db.office.id]['rubric_id']

                        if json_reader.section.rubric_id == TOfficeRubrics.Municipality and  \
                                convert_municipality_to_education(json_reader.section.position):
                            json_reader.section.rubric_id = TOfficeRubrics.Education

                        json_reader.save_to_database(section_id)
                        imported_section_years.append(income_year)

                except (DatabaseError, TSmartParserJsonReader.SerializerException) as exp:
                    TImporter.logger.error("Error! cannot import section N {}: {} ".format(section_index, exp))

        if len(imported_section_years) > 0:
            source_document_in_db.min_income_year = min(imported_section_years)
            source_document_in_db.max_income_year = max(imported_section_years)
            source_document_in_db.section_count = len(imported_section_years)
            source_document_in_db.save()

        return len(imported_section_years)

    def get_smart_parser_json(self, all_imported_human_jsons, sha256, src_doc):
        response = self.smart_parser_cache_client.retrieve_json_by_sha256(sha256)
        if response is None  or  response == {}:
            return self.get_human_smart_parser_json(src_doc, all_imported_human_jsons)
        else:
            return response

    def import_office(self, office_id):
        all_imported_human_jsons = set()

        for sha256 in self.office_to_source_documents[office_id]:
            src_doc = self.dlrobot_human.document_collection[sha256]
            assert src_doc.calculated_office_id == office_id
            smart_parser_json = self.get_smart_parser_json(all_imported_human_jsons, sha256, src_doc)
            doc_file_in_db = self.register_document_in_database(sha256, src_doc)
            if smart_parser_json is None:
                self.logger.debug("file {} has no valid smart parser json, skip it".format(sha256))
            else:
                try:
                    sections_count = self.import_one_smart_parser_json(src_doc.get_declarator_income_year(), doc_file_in_db, smart_parser_json)
                    TImporter.logger.debug("import {} sections from {}".format(sections_count, sha256))
                except TSmartParserJsonReader.SerializerException as exp:
                    TImporter.logger.error("Error! cannot import smart parser json for file {}: {} ".format(sha256, exp))


def process_one_file_in_subprocess(importer: TImporter, office_id):
    importer.init_after_fork()
    try:
        importer.import_office(office_id)
        gc.collect()
    except TSmartParserJsonReader.SerializerException as exp:
        TImporter.logger.error("cannot import office {}, exception: {}".format(office_id), exp)


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
        parser.add_argument(
            '--permanent-links-db',
            dest='permanent_links_db',
            required=True
        )

    def handle(self, *args, **options):
        TImporter.logger = setup_logging("import_json.log")
        importer = TImporter(options)
        stop_elastic_indexing()

        self.stdout.write("start importing")
        if options.get('process_count', 0) > 1:
            importer.delete_before_fork()
            pool = Pool(processes=options.get('process_count'))
            pool.map(partial(process_one_file_in_subprocess, importer), importer.office_to_source_documents.keys())
            importer.init_after_fork()
        else:
            importer.init_non_pickable()
            cnt = 0
            for office_id in importer.office_to_source_documents.keys():
                if options.get('take_first_n_offices') is not None and cnt >= options.get('take_first_n_offices'):
                    break
                importer.import_office(office_id)
                cnt += 1

        start_elastic_indexing()
        TImporter.logger.info("Section count={}".format(models.Section.objects.all().count()))
        TImporter.logger.info("all done")

Command=ImportJsonCommand
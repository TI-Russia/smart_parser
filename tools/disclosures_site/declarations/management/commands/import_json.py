import declarations.models as models
from declarations.serializers import TSmartParserSectionJson
from declarations.permalinks import TPermaLinksSection, TPermaLinksSourceDocument
from smart_parser_http.smart_parser_client import TSmartParserCacheClient
from declarations.input_json import TDlrobotHumanFile, TSourceDocument
from common.logging_wrapper import setup_logging

from multiprocessing import Pool
import os
from functools import partial
import json
from collections import defaultdict
from django.core.management import BaseCommand
from django.db import transaction
from django.db import DatabaseError
import gc
from statistics import median


class TImporter:
    logger = None
    max_vehicle_count = 60

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
        self.permalinks_db_section = None
        self.permalinks_db_source_document = None
        self.smart_parser_cache_client = None

    def delete_before_fork(self):
        from django import db
        db.connections.close_all()

    def init_non_pickable(self):
        self.smart_parser_cache_client = TSmartParserCacheClient(TSmartParserCacheClient.parse_args([]), TImporter.logger)

        self.permalinks_db_section = TPermaLinksSection(self.args['permalinks_folder'])
        self.permalinks_db_section.open_db_read_only()
        self.permalinks_db_source_document = TPermaLinksSourceDocument(self.args['permalinks_folder'])
        self.permalinks_db_source_document.open_db_read_only()

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
                                                       intersection_status=src_doc.build_intersection_status(),
                                                       )
        source_document_in_db.id, new_file = self.permalinks_db_source_document.get_source_doc_id_by_sha256(sha256)
        assert not models.Source_Document.objects.filter(id=source_document_in_db.id).exists()
        self.logger.debug("register doc sha256={} id={}, new_file={}".format(sha256, source_document_in_db.id, new_file))
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

    def calc_income_year(self, input_json, src_doc: TSourceDocument, section_json, section_index):
        # do not use here default value for get, since smart_parser explicitly write "year": null
        year = section_json.get('year')
        if year is not None:
            return int(year)

        # take income_year from the document heading
        year = input_json.get('document', dict()).get('year')

        # If absent, take it from declarator db
        if year is None:
            year = src_doc.get_declarator_income_year()

        # If absent, take it from html anchor text
        if year is None:
            year = src_doc.get_external_income_year_from_dlrobot()

        # otherwise the file is useless
        if year is None:
            raise TSmartParserSectionJson.SerializerException(
                "year is not defined: section No {}".format(section_index))

        return int(year)

    def import_one_smart_parser_json(self, source_document_in_db, input_json, src_doc: TSourceDocument):
        imported_section_years = list()
        section_index = 0
        TImporter.logger.debug("try to import {} declarants".format(len(input_json['persons'])))
        incomes = list()

        for raw_section in input_json['persons']:
            section_index += 1
            section_income_year = self.calc_income_year(input_json, src_doc,  raw_section, section_index)
            with transaction.atomic():
                try:
                    prepared_section = TSmartParserSectionJson(section_income_year, source_document_in_db)
                    prepared_section.read_raw_json(raw_section)

                    if len(prepared_section.vehicles) > TImporter.max_vehicle_count:
                        TImporter.logger.debug("ignore section {} because it has too many vehicles ( > {})".format(
                            prepared_section.section.person_name, TImporter.max_vehicle_count))
                        continue
                    passport1 = prepared_section.get_passport_components1().get_main_section_passport()
                    if self.register_section_passport(passport1):
                        prepared_section.section.tmp_income_set = prepared_section.incomes
                        passport2 = prepared_section.get_passport_components2().get_main_section_passport()
                        section_id, is_new = self.permalinks_db_section.get_section_id(passport1, passport2)
                        if is_new:
                            TImporter.logger.debug("found a new section {}, set section.id to {}".format(
                                prepared_section.section.get_permalink_passport(), section_id))

                        main_income = prepared_section.get_main_declarant_income_size()
                        if main_income is not None and main_income > 0:
                            incomes.append(main_income)
                        prepared_section.save_to_database(section_id)
                        imported_section_years.append(section_income_year)

                except (DatabaseError, TSmartParserSectionJson.SerializerException) as exp:
                    TImporter.logger.error("Error! cannot import section N {}: {} ".format(section_index, exp))

        if len(imported_section_years) > 0:
            source_document_in_db.min_income_year = min(imported_section_years)
            source_document_in_db.max_income_year = max(imported_section_years)
            source_document_in_db.section_count = len(imported_section_years)
            median_income = 0
            if len(incomes) > 0:
                median_income = median(incomes)
            if median_income >= 2**31:
                median_income = 0
            source_document_in_db.median_income = median_income
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
        max_doc_id = 2**32
        ordered_documents = list()
        for sha256 in self.office_to_source_documents[office_id]:
            doc_id = self.permalinks_db_source_document.get_old_source_doc_id_by_sha256(sha256)
            if doc_id is None:
                doc_id = max_doc_id
            ordered_documents.append((doc_id, sha256))
        ordered_documents.sort()

        for _, sha256 in ordered_documents:
            src_doc = self.dlrobot_human.document_collection[sha256]
            assert src_doc.calculated_office_id == office_id
            smart_parser_json = self.get_smart_parser_json(all_imported_human_jsons, sha256, src_doc)
            doc_file_in_db = self.register_document_in_database(sha256, src_doc)
            if smart_parser_json is None:
                self.logger.debug("file {} has no valid smart parser json, skip it".format(sha256))
            else:
                try:
                    sections_count = self.import_one_smart_parser_json(
                        doc_file_in_db, smart_parser_json,  src_doc)
                    TImporter.logger.debug("import {} sections from {}".format(sections_count, sha256))
                except TSmartParserSectionJson.SerializerException as exp:
                    TImporter.logger.error("Error! cannot import smart parser json for file {}: {} ".format(sha256, exp))


def process_one_file_in_subprocess(importer: TImporter, office_id):
    importer.init_after_fork()
    try:
        importer.import_office(office_id)
        gc.collect()
    except TSmartParserSectionJson.SerializerException as exp:
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
            '--take-first-n-web_site_snapshots',
            dest='take_first_n_offices',
            required=False,
            type=int,
        )
        parser.add_argument(
            '--permalinks-folder',
            dest='permalinks_folder',
            required=True
        )
        parser.add_argument(
            '--office-id',
            dest='office_id',
            type=int,
            required=False
        )

    def handle(self, *args, **options):
        TImporter.logger = setup_logging(log_file_name="import_json.log")
        importer = TImporter(options)

        self.stdout.write("start importing")
        if options.get('office_id') is not None:
            importer.init_non_pickable()
            importer.import_office(options.get('office_id'))
        elif options.get('process_count', 0) > 1:
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

        TImporter.logger.info("Section count={}".format(models.Section.objects.all().count()))
        TImporter.logger.info("all done")

Command=ImportJsonCommand

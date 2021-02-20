import declarations.models as models
import declarations.documents as elastic_documents
from elasticsearch import helpers
from declarations.car_brands import CAR_BRANDS
from common.primitives import prepare_russian_names_for_search_index

from itertools import groupby
from operator import itemgetter
from django.core.management import BaseCommand
import logging
import os
from django.conf import settings
from elasticsearch import Elasticsearch
from django.db import connection


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


def fetch_cursor(sql_query):
    with connection.cursor() as cursor:
        cursor.execute(sql_query)
        while True:
            results = cursor.fetchmany(10000)
            if not results:
                break
            for x in results:
                yield x


class TOfficeElasticIndexator:
    def __init__(self, logger):
        self.logger = logger
        self.index_name = settings.ELASTICSEARCH_INDEX_NAMES['office_index_name']
        self.index = elastic_documents.office_search_index
        self.logger.debug("index offices")

    def gen_documents(self):
        for o in models.Office.objects.all():
            yield {
                "_id": o.id,
                "_index": self.index_name,
                "_source": {
                        'id': o.id,
                        'name': o.name,
                        'parent_id': o.parent_id,
                        'source_document_count': o.source_document_count,
                        'rubric_id': o.rubric_id,
                    }
                }


class TIncomeIterator:
    def __init__(self, begin, end):
        self.current_section_id = None
        self.current_incomes = None
        self.query = """
            select section_id, id, size, relative
            from declarations_income
            where section_id >= {} and section_id < {}
            order by section_id  
        """.format(begin, end)
        self.incomes = self.gen_incomes()

    def gen_incomes(self):
        with connection.cursor() as cursor:
            cursor.execute(self.query)
            for section_id, incomes in groupby(cursor, itemgetter(0)):
                self.current_incomes = incomes
                self.current_section_id = section_id
                yield section_id

    def get_incomes_by_section_id(self, section_id):
        declarant_income = None
        spouse_income = None
        while self.current_section_id is None or self.current_section_id < section_id:
            try:
                self.incomes.__next__()
            except StopIteration:
                return declarant_income, spouse_income
        if self.current_section_id == section_id:
            for section_id, id, income_size, relative in self.current_incomes:
                if relative == models.Relative.main_declarant_code:
                    declarant_income = income_size
                elif relative == models.Relative.spouse_code:
                    spouse_income = income_size
        return declarant_income, spouse_income


class TVehicleIterator:
    def __init__(self, begin, end):
        self.current_section_id = None
        self.current_vehicles = None
        self.vehicles = self.gen_vehicles()
        self.query = """
            select section_id, id, name
            from declarations_vehicle
            where length(name) > 1 and
                 section_id >= {} and section_id < {}
            order by section_id  
        """.format(begin, end)

    def gen_vehicles(self):
        with connection.cursor() as cursor:
            cursor.execute(self.query)
            for section_id, vehicles in groupby(cursor, itemgetter(0)):
                self.current_vehicles = vehicles
                self.current_section_id = section_id
                yield section_id

    def get_vehicles_by_section_id(self, section_id):
        car_brands = set()
        while self.current_section_id is None or self.current_section_id < section_id:
            try:
                self.vehicles.__next__()
            except StopIteration:
                return list(car_brands)
        if self.current_section_id == section_id:
            for section_id, id, name in self.current_vehicles:
                car_brands.update(CAR_BRANDS.find_brands(name))
        return list(car_brands)


def prepare_position_and_department(position, department):
    str = ""
    if position is not None:
        str += position
    if department is not None:
        if len(str) > 0:
            str += " "
        str += department
    return str


class TSectionElasticIndexator:
    chunk_size = 100000

    def __init__(self, logger):
        self.logger = logger
        self.index_name = settings.ELASTICSEARCH_INDEX_NAMES['section_index_name']
        self.index = elastic_documents.section_search_index
        self.logger.debug("index sections")

    def gen_document_portion(self, begin, end):
        query = """
            select s.id, d.id, d.office_id, s.position, s.department, s.person_id, o.region_id, 
                  s.income_year, d.office_id, s.person_name, s.rubric_id, s.income_year
            from declarations_section s 
            join declarations_source_document d on d.id=s.source_document_id 
            join declarations_office o on d.office_id=o.id
            where s.id >= {} and s.id < {}
            order by s.id
        """.format(begin, end)
        income_iterator = TIncomeIterator(begin, end)
        vehicle_iterator = TVehicleIterator(begin, end)
        sections_iterator = fetch_cursor(query)
        for section_id, source_document_id, office_id, position, department, \
            person_id, region_id, income_year, office_id, person_name, rubric_id, income_year in sections_iterator:

            declarant_income, spouse_income = income_iterator.get_incomes_by_section_id(section_id)
            car_brands = vehicle_iterator.get_vehicles_by_section_id(section_id)
            position_and_department = prepare_position_and_department(position, department)
            if region_id is None:
                region_id = 0
            yield {
                "_id": section_id,
                "_index": self.index_name,
                "_source": {
                        'id': section_id,
                        'source_document_id': source_document_id,
                        'office_id': office_id,
                        'position_and_department': position_and_department,
                        'income_size': declarant_income,
                        'spouse_income_size': spouse_income,
                        'person_id': person_id,
                        'region_id': int(region_id),
                        'car_brands': car_brands,
                        'person_name': prepare_russian_names_for_search_index(person_name),
                        'rubric_id': rubric_id,
                        'income_year': income_year
                    }
                }

    def gen_documents(self):
        if models.Section.objects.count() == 0:
            max_id = 1
        else:
            max_id = models.Section.objects.all().order_by('-id').first().pk + 1
        for start in range(0, max_id, self.chunk_size):
            self.logger.debug("sections from {} to {}".format(start, start + self.chunk_size))
            for d in self.gen_document_portion(start, start + self.chunk_size):
                yield d


class TPersonElasticIndexator:

    chunk_size = 100000

    def __init__(self, logger):
        self.logger = logger
        self.index_name = settings.ELASTICSEARCH_INDEX_NAMES['person_index_name']
        self.index = elastic_documents.person_search_index
        self.logger.debug("index persons")

    def gen_document_portion(self, begin, end):
        query = """
            select p.id, p.person_name, count(s.id) 
            from declarations_person p 
            join declarations_section s on p.id=s.person_id
            where p.id >= {} and p.id < {}
            group by(p.id) 
        """.format(begin, end)
        for person_id, person_name, section_count in fetch_cursor(query):
            yield {
                "_id": person_id,
                "_index": self.index_name,
                "_source": {
                        'id': person_id,
                        'person_name': prepare_russian_names_for_search_index(person_name),
                        'section_count': section_count
                    }
                }

    def gen_documents(self):
        if models.Person.objects.count() == 0:
            max_id = 1
        else:
            max_id = models.Person.objects.all().order_by('-id').first().pk + 1
        for start in range(0, max_id, self.chunk_size):
            self.logger.debug("persons from {} to {}".format(start, start + self.chunk_size))
            for d in self.gen_document_portion(start, start + self.chunk_size):
                yield d


class TWebReferenceIterator:

    def __init__(self):
        self.current_source_document_id = None
        self.current_web_references = []
        self.web_references = self.gen_web_references()

    def gen_web_references(self):
        query = """
            select source_document_id, crawl_epoch, web_domain
            from declarations_web_reference
            order by source_document_id  
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            for source_document_id, refs in groupby(cursor, itemgetter(0)):
                self.current_web_references = refs
                self.current_source_document_id = source_document_id
                yield source_document_id

    def get_squeeze_by_source_document_id(self, doc_id):
        while self.current_source_document_id is None or self.current_source_document_id < doc_id:
            try:
                self.web_references.__next__()
            except StopIteration:
                return None, set()
        if self.current_source_document_id == doc_id:
            min_crawl_epoch = None
            web_domains = set()
            for id, crawl_epoch, web_domain in self.current_web_references:
                if min_crawl_epoch is None:
                    min_crawl_epoch = crawl_epoch
                else:
                    min_crawl_epoch = min(min_crawl_epoch, crawl_epoch)
                web_domains.add(web_domain)
            return min_crawl_epoch, web_domains
        return None, set()


class TDeclaratorFileReferenceIterator:
    def __init__(self):
        self.current_source_document_id = None
        self.current_references = []
        self.references = self.gen_references()

    def gen_references(self):
        query = """
            select source_document_id,  web_domain
            from declarations_declarator_file_reference
            order by source_document_id  
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            for source_document_id, refs in groupby(cursor, itemgetter(0)):
                self.current_references = refs
                self.current_source_document_id = source_document_id
                yield source_document_id

    def get_squeeze_by_source_document_id(self, doc_id):
        while self.current_source_document_id is None or self.current_source_document_id < doc_id:
            try:
                self.references.__next__()
            except StopIteration:
                return set()
        if self.current_source_document_id == doc_id:
            web_domains = set()
            for id, web_domain in self.current_references:
                web_domains.add(web_domain)
            return web_domains
        return set()


class TSourceDocumentElasticIndexator:
    def __init__(self, logger):
        self.logger = logger
        self.index_name = settings.ELASTICSEARCH_INDEX_NAMES['file_index_name']
        self.index = elastic_documents.file_search_index
        self.logger.debug("index source documents")

    def gen_documents(self):
        query = """
            select id, office_id, intersection_status, min_income_year, max_income_year, section_count, sha256 
            from declarations_source_document
            order by id 
        """
        web_ref_iter = TWebReferenceIterator()
        declarator_file_ref_iter = TDeclaratorFileReferenceIterator()
        doc_iterator = fetch_cursor(query)
        cnt = 0
        for id, office_id, intersection_status, min_income_year, max_income_year, section_count, sha256 in doc_iterator:
            first_crawl_epoch, web_domains = web_ref_iter.get_squeeze_by_source_document_id(id)
            web_domains.update(declarator_file_ref_iter.get_squeeze_by_source_document_id(id))
            cnt += 1
            yield {
                "_id": id,
                "_index": self.index_name,
                "_source": {
                        'id': id,
                        'office_id': office_id,
                        'intersection_status': intersection_status,
                        'min_income_year': min_income_year,
                        'max_income_year': max_income_year,
                        'section_count': section_count,
                        'sha256': sha256,
                        'first_crawl_epoch': first_crawl_epoch,
                        'web_domains': " ".join(web_domains),
                    }
                }
        self.logger.debug("number of sent documents: {}".format(cnt))


def rebuild(indexator):
    indexator.logger.debug("delete {}".format(indexator.index_name))
    indexator.index.delete()

    indexator.logger.debug("create {}".format(indexator.index_name))
    indexator.index.create()
    es = Elasticsearch()
    helpers.bulk(es, indexator.gen_documents())
    indexator.index.flush()
    indexator.index.refresh()
    indexator.logger.debug("all done")


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = None
        self.logger = None

    def add_arguments(self, parser):
        parser.add_argument(
                '--model',
            dest='model',
            help='model name: office, section, person or source_document'
        )
        parser.add_argument(
                '--logfile',
            dest='logfile',
            default="build_elastic.log"
        )

    def handle(self, *args, **options):
        self.logger = setup_logging(options.get('logfile', 'build_elastic.log'))
        model = options.get('model')
        if model == 'office' or model is None:
            rebuild(TOfficeElasticIndexator(self.logger))
        if model == 'section' or model is None:
            rebuild(TSectionElasticIndexator(self.logger))
        if model == 'person' or model is None:
            rebuild(TPersonElasticIndexator(self.logger))
        if model == 'source_document' or model is None:
            rebuild(TSourceDocumentElasticIndexator(self.logger))


BuildElasticIndex=Command

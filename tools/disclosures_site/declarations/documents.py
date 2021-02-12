from django_elasticsearch_dsl import Document, IntegerField, TextField, ListField
from django_elasticsearch_dsl.registries import registry
from declarations.models import Section, Person, Office, Source_Document, TOfficeTableInMemory
from django.conf import settings
from elasticsearch_dsl import Index
from django.db.utils import DatabaseError
from datetime import datetime

section_search_index = Index(settings.ELASTICSEARCH_INDEX_NAMES['section_index_name'])
section_search_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

OFFICES = None

@registry.register_document
@section_search_index.document
class ElasticSectionDocument(Document):
    default_field_name = "person_name"
    source_document_id = IntegerField()
    office_id = IntegerField()
    position_and_department = TextField()
    income_size = IntegerField()
    spouse_income_size = IntegerField()
    person_id = IntegerField()
    region_id = IntegerField()

    class Django:
        model = Section
        fields = [
            'id',
            'person_name',
            'income_year',
            'rubric_id'
        ]

    def prepare_source_document_id(self, instance):
        return instance.source_document_id

    def prepare_office_id(self, instance):
        return instance.source_document.office.id

    def prepare_region_id(self, instance):
        region_id = instance.source_document.office.region_id
        if region_id  is None:
            return 0 # there is no sql record with  region_id = 0
        else:
            return region_id

    def prepare_position_and_department(self, instance):
        str = ""
        if instance.position is not None:
            str += instance.position
        if instance.department is not None:
            if len(str) > 0:
                str += " "
            str += instance.department
        return str

    def prepare_income_size(self, instance):
        return instance.get_declarant_income_size()

    def prepare_spouse_income_size(self, instance):
        return instance.get_spouse_income_size()

    def prepare_person_id(self, instance):
        return instance.person_id


person_search_index = Index(settings.ELASTICSEARCH_INDEX_NAMES['person_index_name'])
person_search_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@registry.register_document
@person_search_index.document
class ElasticPersonDocument(Document):
    default_field_name = "person_name"
    section_count = IntegerField()

    class Django:
        model = Person
        fields = [
            'id',
            'person_name',
        ]
    def prepare_section_count(self, instance):
        return instance.section_count


office_search_index = Index(settings.ELASTICSEARCH_INDEX_NAMES['office_index_name'])
office_search_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@registry.register_document
@office_search_index.document
class ElasticOfficeDocument(Document):
    default_field_name = "name"
    parent_id = IntegerField()
    source_document_count = IntegerField()

    class Django:
        model = Office
        fields = [
            'id',
            'name',
        ]

    def prepare_parent_id(self, instance):
        assert OFFICES is not None
        return instance.parent_id

    def prepare_source_document_count(self, instance):
        return instance.source_document_count


file_search_index = Index(settings.ELASTICSEARCH_INDEX_NAMES['file_index_name'])
file_search_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@registry.register_document
@file_search_index.document
class ElasticFileDocument(Document):
    office_id = IntegerField()
    first_crawl_epoch = IntegerField()
    web_domains = TextField()

    class Django:
        model = Source_Document
        fields = [
            'id',
            'intersection_status',
            'min_income_year',
            'max_income_year',
            'section_count',
            'sha256'
        ]

    def prepare_office_id(self, instance):
        return instance.office_id

    def prepare_first_crawl_epoch(self, instance):
        min_crawl_epoch = None
        for web_ref in instance.web_reference_set.all():
            if min_crawl_epoch is None:
                min_crawl_epoch = web_ref.crawl_epoch
            else:
                min_crawl_epoch = min(min_crawl_epoch, web_ref.crawl_epoch)
        return min_crawl_epoch

    @property
    def get_first_crawl_epoch_str(self):
        if self.first_crawl_epoch is None:
            return ''
        return datetime.fromtimestamp(self.first_crawl_epoch).strftime("%Y-%m-%d")

    def prepare_web_domains(self, instance):
        web_domains = set()
        for ref in instance.web_reference_set.all():
            if ref.web_domain is not None:
                web_domains.add(ref.web_domain)
        for ref in instance.declarator_file_reference_set.all():
            if ref.web_domain is not None:
                web_domains.add(ref.web_domain)
        return " ".join(web_domains)


def stop_elastic_indexing():
    ElasticOfficeDocument.django.ignore_signals = True
    ElasticSectionDocument.django.ignore_signals = True
    ElasticPersonDocument.django.ignore_signals = True
    ElasticFileDocument.django.ignore_signals = True


def start_elastic_indexing():
    ElasticOfficeDocument.django.ignore_signals = False
    ElasticSectionDocument.django.ignore_signals = False
    ElasticPersonDocument.django.ignore_signals = False
    ElasticFileDocument.django.ignore_signals = False


try:
    OFFICES = TOfficeTableInMemory()
except DatabaseError as exp:
    stop_elastic_indexing()
    print("stop_elastic_indexing because there is no offices")

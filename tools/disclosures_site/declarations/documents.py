from django_elasticsearch_dsl import Document, IntegerField, TextField, ListField, KeywordField
from django_elasticsearch_dsl.registries import registry
from declarations.models import Section, Person, Office, Source_Document, TOfficeTableInMemory
from django.conf import settings
from elasticsearch_dsl import Index
from django.db.utils import DatabaseError
from datetime import datetime

#We do not support elaastic index updates on a single sql db edit.
#Elastic indices are created in disclosures_site/declarations/management/commands/build_elastic_index.py via sql queries,
#since it is faster than prepare_field* mechanics.

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
    car_brands = KeywordField()

    class Django:
        model = Section
        fields = [
            'id',
            'person_name',
            'income_year',
            'rubric_id'
        ]


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


def stop_elastic_indexing():
    ElasticOfficeDocument.django.ignore_signals = True
    ElasticSectionDocument.django.ignore_signals = True
    ElasticPersonDocument.django.ignore_signals = True
    ElasticFileDocument.django.ignore_signals = True


stop_elastic_indexing()

try:
     OFFICES = TOfficeTableInMemory()
except DatabaseError as exp:
    pass

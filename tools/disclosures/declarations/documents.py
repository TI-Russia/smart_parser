from django_elasticsearch_dsl import Document, IntegerField
from django_elasticsearch_dsl.registries import registry
from declarations.models import Section, Person, Office, Source_Document
from django.conf import settings
from elasticsearch_dsl import Index

section_search_index = Index(settings.ELASTICSEARCH_INDEX_NAMES['section_index_name'])
section_search_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@registry.register_document
@section_search_index.document
class ElasticSectionDocument(Document):
    default_field_name = "person_name"
    source_document_id = IntegerField()
    class Django:
        model = Section
        fields = [
            'id',
            'person_name',
        ]

    def prepare_source_document_id(self, instance):
        return instance.source_document_id


person_search_index = Index(settings.ELASTICSEARCH_INDEX_NAMES['person_index_name'])
person_search_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@registry.register_document
@person_search_index.document
class ElasticPersonDocument(Document):
    default_field_name = "person_name"
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

    class Django:
        model = Office
        fields = [
            'id',
            'name',
        ]

    def prepare_parent_id(self, instance):
        return instance.parent_id


file_search_index = Index(settings.ELASTICSEARCH_INDEX_NAMES['file_index_name'])
file_search_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@registry.register_document
@file_search_index.document
class ElasticFileDocument(Document):
    office_id = IntegerField()
    default_field_name = "file_path"

    class Django:
        model = Source_Document
        fields = [
            'id',
            'file_path',
        ]

    def prepare_office_id(self, instance):
        return instance.office_id


def stop_elastic_indexing():
    ElasticSectionDocument.django.ignore_signals = True
    ElasticPersonDocument.django.ignore_signals = True
    ElasticFileDocument.django.ignore_signals = True


def start_elastic_indexing():
    ElasticSectionDocument.django.ignore_signals = False
    ElasticPersonDocument.django.ignore_signals = False
    ElasticFileDocument.django.ignore_signals = False
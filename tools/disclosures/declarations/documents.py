from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.registries import registry
from declarations.models import Section, Person
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
    class Django:
        model = Section
        fields = [
            'id',
            'person_name',
        ]


person_search_index = Index(settings.ELASTICSEARCH_INDEX_NAMES['person_index_name'])
person_search_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@registry.register_document
@person_search_index.document
class ElasticPersonDocument(Document):
    class Django:
        model = Person
        fields = [
            'id',
            'person_name',
        ]


def stop_elastic_indexing():
    ElasticSectionDocument.django.ignore_signals = True
    ElasticPersonDocument.django.ignore_signals = True


def start_elastic_indexing():
    ElasticSectionDocument.django.ignore_signals = False
    ElasticPersonDocument.django.ignore_signals = False
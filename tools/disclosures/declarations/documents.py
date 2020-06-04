from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.registries import registry
from declarations.models import Section
from django.conf import settings


@registry.register_document
class ElasticSectionDocument(Document):
    class Index:
        name = settings.ELASTICSEARCH_INDEX_NAMES['section_index_name']
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}
    class Django:
        model = Section
        fields = [
            'id',
            'person_name',
        ]

@registry.register_document
class ElasticPersonDocument(Document):
    class Index:
        name = settings.ELASTICSEARCH_INDEX_NAMES['person_index_name']
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}
    class Django:
        model = Section
        fields = [
            'id',
            'person_name',
        ]


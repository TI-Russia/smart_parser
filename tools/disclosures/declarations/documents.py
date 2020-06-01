from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.registries import registry
from .models import Section


@registry.register_document
class ElasticSectionDocument(Document):
    class Index:
        name = 'declaration_sections'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}
    class Django:
        model = Section
        fields = [
            'id',
            'person_name',
        ]



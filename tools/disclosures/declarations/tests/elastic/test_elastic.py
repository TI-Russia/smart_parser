from django.test import TestCase
import declarations.models as models
from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.registries import registry
import time


@registry.register_document
class ElasticSectionDocumentTest(Document):
    class Index:
        name = 'declaration_sections_test'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = models.Section
        fields = [
            'id',
            'person_name',
        ]



class ElasticTestCase(TestCase):

    def test_elastic(self):
        ElasticSectionDocumentTest.init()
        ElasticSectionDocumentTest.search().query().delete()
        time.sleep(2)
        people = list(ElasticSectionDocumentTest.search().query('match', person_name='Иванов'))
        self.assertEqual(len(people), 0)
        people = list(ElasticSectionDocumentTest.search().query('match', person_name='Иванов'))
        models.Section.objects.all().delete()
        section = models.Section()
        section.person_name = "Иванов Иван"
        section.save()
        time.sleep(3)

        people = list(ElasticSectionDocumentTest.search().query('match', person_name='Иванов'))
        print (len(people))
        self.assertEqual(len(people), 1)

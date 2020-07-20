from django.test import TestCase
import declarations.models as models
import time
from declarations.documents import ElasticSectionDocument


class ElasticTestCase(TestCase):

    def test_elastic(self):
        ElasticSectionDocument.init()
        ElasticSectionDocument._index._name.endswith("_test")
        ElasticSectionDocument.search().query().delete()
        time.sleep(2)
        people = list(ElasticSectionDocument.search().query('match', person_name='Иванов'))
        self.assertEqual(len(people), 0)
        people = list(ElasticSectionDocument.search().query('match', person_name='Иванов'))
        models.Section.objects.all().delete()
        section = models.Section()
        section.person_name = "Иванов Иван"
        section.save()
        print("sleep 2 seconds till elastic processes records")
        time.sleep(2)

        people = list(ElasticSectionDocument.search().query('match', person_name='Иванов'))
        print (len(people))
        self.assertEqual(len(people), 1)

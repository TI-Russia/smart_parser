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
        models.Source_Document.objects.all().delete()

        ofc = models.Office()
        ofc.name = "some name"
        ofc.save()

        src_doc = models.Source_Document()
        src_doc.office  = ofc
        src_doc.save()

        section = models.Section()
        section.person_name = "Иванов Иван"
        section.source_document = src_doc
        section.save()
        print("sleep 2 seconds till elastic processes records")
        time.sleep(2)

        people = list(ElasticSectionDocument.search().query('match', person_name='Иванов'))
        print (len(people))
        self.assertEqual(len(people), 1)

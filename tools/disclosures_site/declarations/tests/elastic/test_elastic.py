from django.test import TestCase
import declarations.models as models
import time
from declarations.documents import ElasticSectionDocument, section_search_index


class ElasticTestCase(TestCase):

    def test_elastic(self):
        self.assertGreater(models.Office.objects.count(), 0)

        ElasticSectionDocument.init()
        ElasticSectionDocument._index._name.endswith("_test")
        ElasticSectionDocument.search().query().delete()
        time.sleep(2)
        people = list(ElasticSectionDocument.search().query('match', person_name='Иванов'))
        self.assertEqual(len(people), 0)
        people = list(ElasticSectionDocument.search().query('match', person_name='Иванов'))
        models.Section.objects.all().delete()
        self.assertEqual(models.Section.objects.count(), 0)
        models.Source_Document.objects.all().delete()

        ofc = models.Office.objects.get(id=1)

        src_doc = models.Source_Document()
        src_doc.id = 1
        src_doc.office = ofc
        src_doc.save()

        section = models.Section()
        section.id = 1
        section.person_name = "Иванов Иван"
        section.source_document = src_doc
        section.save()

        if section_search_index.exists():
            section_search_index.delete()
        section_search_index.create()
        qs = ElasticSectionDocument().get_indexing_queryset()
        ElasticSectionDocument().update(qs)
        people = list(ElasticSectionDocument.search().query('match', person_name='Иванов'))
        self.assertEqual(len(people), 1)

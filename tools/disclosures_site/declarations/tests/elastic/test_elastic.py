from django.test import TestCase, tag
import declarations.models as models
import time
from declarations.documents import ElasticSectionDocument
from declarations.management.commands.build_elastic_index import BuildElasticIndex, TSectionElasticIndexator
from elasticsearch_dsl import Index
from django.conf import settings
from elasticsearch import Elasticsearch


class ElasticTestCase(TestCase):
    @tag('front')
    def test_elastic(self):
        self.assertGreater(models.Office.objects.count(), 0)

        #delete all documents
        index = Index(settings.ELASTICSEARCH_INDEX_NAMES['section_index_name'], Elasticsearch())
        index.delete()
        index.create()
        time.sleep(2)

        #search to get no results
        people = list(ElasticSectionDocument.search().query('match', person_name='Иванов'))
        self.assertEqual(len(people), 0)

        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()

        ofc = models.Office.objects.get(id=1)

        src_doc = models.Source_Document()
        src_doc.id = 1
        src_doc.save()

        models.Section(id=1, person_name="Иванов Иван", source_document=src_doc, office=ofc).save()
        models.Section(id=2, person_name="Петров Петр", source_document=src_doc, office=ofc).save()
        models.Section(id=3, person_name="Сидоров Федор", source_document=src_doc, office=ofc).save()

        #reindex section index
        TSectionElasticIndexator.chunk_size = 2
        BuildElasticIndex(None, None).handle(None, model="section")
        time.sleep(2)
        people = list(ElasticSectionDocument.search().query('match', person_name='Иванов'))
        self.assertEqual(len(people), 1)

        people = list(ElasticSectionDocument.search().query('match', person_name='Петров'))
        self.assertEqual(len(people), 1)

        people = list(ElasticSectionDocument.search().query('match', person_name='Сидоров'))
        self.assertEqual(len(people), 1)

        people = list(ElasticSectionDocument.search().query('match', person_name='Сокирко'))
        self.assertEqual(len(people), 0)

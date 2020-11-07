from django.test import TestCase
from declarations.management.commands.import_json import ImportJsonCommand
import os
import declarations.models as models
from declarations.tests.test_smart_parser import SmartParserServerForTesting
from declarations.management.commands.permalinks import TPermaLinksDB
from django.test import Client
from bs4 import BeautifulSoup


class FioSearchTestCase(TestCase):

    def check_first_section_found(self, person_name):
        c = Client()
        response = c.get('/section/',  {'person_name': person_name})
        content = response.content
        soup = BeautifulSoup(content, 'html.parser')
        for l in list(soup.findAll('a')):
            href = l.attrs.get('href')
            if href == "/section/1":
                return True
        return False

    def test_search_section_by_person_name(self):
        self.assertGreater(models.Office.objects.count(), 0)
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()
        src_doc = models.Source_Document(id=1, office_id=1)
        src_doc.save()
        sct = models.Section(id=1, person_name="Иванов Иван Иванович", source_document=src_doc)
        sct.save()
        self.assertTrue(self.check_first_section_found("Иванов И.И."))
        self.assertTrue(self.check_first_section_found("Иванов Иван Иванович"))
        self.assertTrue(self.check_first_section_found("Иванов Иван"))

from common.html_parser import THtmlParser
from declarations.management.commands.build_elastic_index import BuildElasticIndex
from django.test import TestCase, tag


class FioSearchMisspellTestCase(TestCase):

    @tag('front')
    def test_search_section_by_misspelled_person_name(self):
        BuildElasticIndex(None, None).handle(None, model="section")
        response = self.client.get("/section/?person_name=Оверьянова Лариса Васильевна")
        html = THtmlParser(response.content)
        i = html.html_with_markup.find("Аверьянова")
        self.assertIsNot(i, -1, "must found a corrected string")

    @tag('front')
    def test_search_person_by_misspelled_person_name(self):
        BuildElasticIndex(None, None).handle(None, model="person") #may be empty, but must exist
        response = self.client.get("/person/?person_name=Оверьянова Лариса Васильевна")
        html = THtmlParser(response.content)
        i = html.html_with_markup.find("Аверьянова")
        self.assertIsNot(i, -1, "must found a corrected string")

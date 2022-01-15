from common.html_parser import THtmlParser

from django.test import TestCase, tag
import declarations.models as models
from declarations.views import SectionSearchView, compare_Russian_fio
from declarations.management.commands.build_elastic_index import BuildElasticIndex


class FioSearchMisspellTestCase(TestCase):

    def search_sections_by_fio(self, person_name):
        view = SectionSearchView()
        class TGetRequest:
            GET = {'person_name': person_name}
        view.request = TGetRequest()
        results = view.get_queryset()
        return results

    @tag('front')
    def test_search_section_by_misspelled_person_name(self):
        self.assertGreater(models.Office.objects.count(), 0)
        response = self.client.get("/section/?person_name=Оверьянова Лариса Васильевна")
        html = THtmlParser(response.content)
        i = html.html_with_markup.find("Аверьянова")
        self.assertIsNot(i, -1, "must found a corrected string")


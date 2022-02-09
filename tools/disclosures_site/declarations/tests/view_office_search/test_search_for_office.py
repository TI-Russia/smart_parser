from django.test import TestCase, tag
import declarations.models as models
from declarations.views import OfficeSearchView
from declarations.management.commands.build_elastic_index import BuildElasticIndex
from declarations.management.commands.build_office_calculated_params import BuildOfficeCalculatedParams
from common.html_parser import THtmlParser


class OfficeSearchTestCase(TestCase):
    @tag('front')
    def test_search_for_office(self):
        self.assertGreater(models.Office.objects.count(), 0)
        BuildOfficeCalculatedParams(None, None).handle(None, directory=".")
        BuildElasticIndex(None, None).handle(None, model="office")

        view = OfficeSearchView()
        class TGetRequest:
            GET = {'rubric_id': 1}
        view.request = TGetRequest()
        results = view.get_queryset()
        self.assertGreater(len(results), 0)

        response = self.client.get("/office/?rubric_id=1")
        html = THtmlParser(response.content)
        rubric_elem = html.soup.find("select", {"name": "rubric_id"}, recursive=True)
        selected_id = rubric_elem.select_one('option:checked')
        self.assertIsNotNone(selected_id)
        self.assertEqual("Суды", selected_id.getText())


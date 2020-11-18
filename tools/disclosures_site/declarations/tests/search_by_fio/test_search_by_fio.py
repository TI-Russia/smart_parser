from django.test import TestCase
import declarations.models as models
from declarations.views import SectionSearchView, compare_Russian_fio

class FioSearchTestCase(TestCase):

    def search_sections_by_fio(self, person_name):
        view = SectionSearchView()
        class TGetRequest:
            GET = {'person_name': person_name}
        view.request = TGetRequest()
        results = view.get_queryset()
        return results


    def test_search_section_by_person_name(self):
        self.assertGreater(models.Office.objects.count(), 0)
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()
        src_doc = models.Source_Document(id=1, office_id=1)
        src_doc.save()
        models.Section(id=1, person_name="Иванов Иван Иванович", source_document=src_doc).save()

        self.assertEqual(self.search_sections_by_fio("Иванов И.И.")[0].id, 1)
        self.assertEqual(self.search_sections_by_fio("Иванов Иван Иванович")[0].id, 1)
        self.assertEqual(self.search_sections_by_fio("Иванов Иван")[0].id, 1)

    def test_search_section_by_partial_person_name(self):
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()
        src_doc = models.Source_Document(id=1, office_id=1)
        src_doc.save()
        models.Section(id=1, person_name="Один Иван Ильич", source_document=src_doc).save()
        models.Section(id=2, person_name="Два Иван Ильич", source_document=src_doc).save()
        models.Section(id=3, person_name="Иван Ильич", source_document=src_doc).save()

        res = self.search_sections_by_fio("Один Иван")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, 1)

        res = self.search_sections_by_fio("Два Иван")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, 2)

        res = self.search_sections_by_fio("Один Иван Ильич")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, 1)

        res = self.search_sections_by_fio("Иван Ильич")
        self.assertEqual(len(res), 3)

        res = self.search_sections_by_fio("Ильич")
        self.assertEqual(len(res), 3)

        res = self.search_sections_by_fio("Один")
        self.assertEqual(len(res), 1)

    def test_fio_compare(self):
        self.assertFalse(compare_Russian_fio("Сокирко Иван Ильич", "Алексей Ильич"))
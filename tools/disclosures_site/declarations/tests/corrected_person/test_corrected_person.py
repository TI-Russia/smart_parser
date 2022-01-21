from django.test import TestCase, tag
import declarations.models as models
from declarations.corrections import SECTION_CORRECTIONS


# corrections by a website user's request
class CorrectedPersonTestCase(TestCase):
    @tag('front')
    def test_corrected_person(self):
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()
        models.Person.objects.all().delete()
        src_doc = models.Source_Document(id=1)
        src_doc.save()
        assert SECTION_CORRECTIONS.get_corrected_section_id(8048661) == 9798543
        models.Person(id=1, person_name="Иванов Иван Ильич").save()
        models.Section(id=8048661, income_year=2016, person_name="Иванов Иван Ильич", source_document=src_doc,
                       office_id=1, person_id=1).save()
        models.Section(id=9798543, income_year=2016, person_name="Иванов Иван Ильич", source_document=src_doc,
                       office_id=1, person_id=1).save()

        person = models.Person.objects.get(id=1)
        sections = person.sections_ordered_by_year
        self.assertEqual(1, len(sections))

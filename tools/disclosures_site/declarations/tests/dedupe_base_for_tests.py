from django.test import TestCase
import declarations.models as models

TEST_OFFICE_ID = 1


class TestDedupeBase(TestCase):
    def initialize(self):
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()
        models.Person.objects.all().delete()
        self.src_doc = models.Source_Document(id=1)
        self.src_doc.save()

    def create_section(self, section_id, person_name, person=None):
        section = models.Section(id=section_id, office_id=TEST_OFFICE_ID,
                              source_document=self.src_doc, person_name=person_name, person=person)
        section.save()
        return section

from declarations.management.commands.generate_dedupe_pairs import RunDedupe
import declarations.models as models
from declarations.permalinks import TPermaLinksPerson
from declarations.management.commands.create_permalink_storage import CreatePermalinksStorageCommand

import os
from django.test import TestCase


def create_default_source_document():
    models.Section.objects.all().delete()
    models.Source_Document.objects.all().delete()
    models.Person.objects.all().delete()
    src_doc = models.Source_Document(id=1)
    src_doc.office_id = 1
    src_doc.save()
    return src_doc


class DividePersonInHalf(TestCase):

    def test(self):
        permalinks_folder = os.path.dirname(__file__)
        src_doc = create_default_source_document()
        models.Section.objects.all().delete()
        models.Person.objects.all().delete()

        person_id = 99
        person = models.Person(id=person_id)
        person.save()
        section1 = models.Section(id=1,
                       source_document=src_doc,
                       person_name="Иванов Иван Иванович",
                       person=person)
        section1.save()

        section2 = models.Section(id=2,
                       source_document=src_doc,
                       person_name="Иванов Иван Иванович",
                       person=person)
        section2.save()

        CreatePermalinksStorageCommand(None, None).handle(None, directory=permalinks_folder)
        TPermaLinksPerson(permalinks_folder).open_db_read_only().recreate_auto_increment_table()

        section1.person = None
        section1.save()

        section2.person = None
        section2.save()

        person.delete()

        run_dedupe = RunDedupe(None, None)
        run_dedupe.handle(None,
                          permalinks_folder=permalinks_folder,
                          write_to_db=True,
                          fake_dedupe=True,
                          separate_sections=True,
                          surname_bounds=',',
                          take_sections_with_empty_income=True,
                          rebuild=True)

        self.assertEqual(models.Person.objects.count(), 2)

        #"person_id" is inherited by the minimal section_id, if there is no other grounds
        sec1 = models.Section.objects.get(id=1)
        self.assertEqual(sec1.person_id, person_id)

        sec2 = models.Section.objects.get(id=2)
        self.assertEqual(sec2.person_id, person_id + 1) # a new person_id




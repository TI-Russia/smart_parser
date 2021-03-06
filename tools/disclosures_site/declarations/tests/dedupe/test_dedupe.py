from declarations.management.commands.generate_dedupe_pairs import RunDedupe
import declarations.models as models
from declarations.permalinks import TPermaLinksPerson
from declarations.management.commands.create_permalink_storage import CreatePermalinksStorageCommand
from common.logging_wrapper import setup_logging

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


class CreateNewPersonId(TestCase):

    def test(self):
        src_doc = create_default_source_document()
        models.Person.objects.all().delete()

        models.Section(id=1, source_document=src_doc, person_name="Иванов Иван Иванович").save()
        models.Section(id=2, source_document=src_doc, person_name="Иванов И. И.").save()
        permalinks_folder = os.path.dirname(__file__)
        TPermaLinksPerson(permalinks_folder).create_and_save_empty_db()
        run_dedupe = RunDedupe(None, None)
        run_dedupe.handle(None,
                          permalinks_folder=permalinks_folder,
                          write_to_db=True,
                          fake_dedupe=True,
                          surname_bounds=',',
                          take_sections_with_empty_income=True,
                          rebuild=True)

        self.assertEqual(models.Person.objects.count(), 1)
        person = models.Person.objects.get(id=1)
        self.assertEqual(person.person_name, "Иванов Иван Иванович")

        sec1 = models.Section.objects.get(id=1)
        self.assertEqual(sec1.person_id, 1)

        sec2 = models.Section.objects.get(id=2)
        self.assertEqual(sec2.person_id, 1)


class UseOldPersonId(TestCase):

    def test(self):
        src_doc = create_default_source_document()
        models.Person.objects.all().delete()

        person_id = 2
        declarator_person_id = 1111
        person = models.Person(
            id=person_id,
            declarator_person_id=declarator_person_id,
            person_name="Иванов Иван Иванович")
        person.save()

        models.Section(id=1, source_document=src_doc, person_name="Иванов Иван Иванович", person=person).save()
        models.Section(id=2, source_document=src_doc, person_name="Иванов И. И.").save()

        permalinks_folder = os.path.dirname(__file__)
        db = TPermaLinksPerson(permalinks_folder)
        db.create_db()
        db.save_dataset(setup_logging())
        #db.save_max_plus_one_primary_key(3)
        db.recreate_auto_increment_table()
        db.close_db()

        run_dedupe = RunDedupe(None, None)
        run_dedupe.handle(None,
                          permalinks_folder=permalinks_folder,
                          write_to_db=True,
                          fake_dedupe=True,
                          surname_bounds=',',
                          take_sections_with_empty_income=True,
                          rebuild=True)

        self.assertEqual(models.Person.objects.count(), 1)
        person = models.Person.objects.get(id=person_id)
        self.assertIsNotNone(person)
        self.assertEqual(declarator_person_id, person.declarator_person_id)

        sec1 = models.Section.objects.get(id=1)
        self.assertEqual(sec1.person_id, person.id)

        sec2 = models.Section.objects.get(id=2)
        self.assertEqual(sec2.person_id, person.id)


class RememberOldPersonId(TestCase):

    def test(self):
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
                       person_name="Иванов И. И.",
                       person=person)
        section2.save()

        section3 = models.Section(id=3,
                                  source_document=src_doc,
                                  person_name="Петров И. И.",
                                  person=None)
        section3.save()

        permalinks_folder = os.path.dirname(__file__)
        db = TPermaLinksPerson(permalinks_folder)
        db.create_db()
        db.save_dataset(setup_logging())
        db.recreate_auto_increment_table()
        db.close_db()

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
                          surname_bounds=',',
                          take_sections_with_empty_income=True,
                          rebuild=True)

        self.assertEqual(models.Person.objects.count(), 1)

        sec1 = models.Section.objects.get(id=1)
        self.assertEqual(sec1.person_id, person_id)

        sec2 = models.Section.objects.get(id=2)
        self.assertEqual(sec2.person_id, person_id)

        sec3 = models.Section.objects.get(id=3)
        self.assertEqual(sec3.person_id, person_id)


class AddNewSectionsToOldPersonId(TestCase):

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
        CreatePermalinksStorageCommand(None, None).handle(None, directory=permalinks_folder)
        TPermaLinksPerson(permalinks_folder).open_db_read_only().recreate_auto_increment_table()

        section1.person = None
        section1.save()

        person.delete()

        section2 = models.Section(id=2,
                       source_document=src_doc,
                       person_name="Иванов И. И.",
                       )
        section2.save()
        section3 = models.Section(id=3,
                       source_document=src_doc,
                       person_name="Иванов И. И.",
                       )
        section3.save()

        run_dedupe = RunDedupe(None, None)
        run_dedupe.handle(None,
                          permalinks_folder=permalinks_folder,
                          write_to_db=True,
                          fake_dedupe=True,
                          surname_bounds=',',
                          take_sections_with_empty_income=True,
                          rebuild=True)

        self.assertEqual(models.Person.objects.count(), 1)

        sec1 = models.Section.objects.get(id=1)
        self.assertEqual(sec1.person_id, person_id)

        sec2 = models.Section.objects.get(id=2)
        self.assertEqual(sec2.person_id, person_id)

        sec3 = models.Section.objects.get(id=3)
        self.assertEqual(sec3.person_id, person_id)


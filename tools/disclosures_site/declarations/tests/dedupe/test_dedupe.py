from declarations.management.commands.generate_dedupe_pairs import RunDedupe
import declarations.models as models
from declarations.permalinks import TPermaLinksPerson
from declarations.management.commands.create_permalink_storage import CreatePermalinksStorageCommand
from common.logging_wrapper import setup_logging
from declarations.tests.dedupe_base_for_tests import TestDedupeBase

import os


class CreateNewPersonId(TestDedupeBase):

    def test(self):
        self.initialize()
        self.create_section(1, "Иванов Иван Иванович")
        self.create_section(2, "Иванов И. И.")

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


class UseOldPersonId(TestDedupeBase):

    def test(self):
        self.initialize()

        person_id = 2
        declarator_person_id = 1111
        person = models.Person(
            id=person_id,
            declarator_person_id=declarator_person_id,
            person_name="Иванов Иван Иванович")
        person.save()

        self.create_section(1, "Иванов Иван Иванович", person)
        self.create_section(2, "Иванов И. И.")

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


class RememberOldPersonId(TestDedupeBase):

    def test(self):
        self.initialize()

        person_id = 99
        person = models.Person(id=person_id)
        person.save()
        section1 = self.create_section(1, "Иванов Иван Иванович", person=person)
        section2 = self.create_section(2, "Иванов И. И.", person=person)
        section3 = self.create_section(3, "Петров И. И.")

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


class AddNewSectionsToOldPersonId(TestDedupeBase):

    def test(self):
        self.initialize()
        permalinks_folder = os.path.dirname(__file__)

        person_id = 99
        person = models.Person(id=person_id)
        person.save()
        section1 = self.create_section(1, "Иванов Иван Иванович", person=person)
        CreatePermalinksStorageCommand(None, None).handle(None, directory=permalinks_folder)
        TPermaLinksPerson(permalinks_folder).open_db_read_only().recreate_auto_increment_table()

        section1.person = None
        section1.save()

        person.delete()

        self.create_section(2, "Иванов И. И.")
        self.create_section(3, "Иванов И. И.")

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


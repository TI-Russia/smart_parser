from declarations.permalinks import TPermaLinksPerson
from declarations.management.commands.copy_person_id import CopyPersonIdCommand, build_section_passport
from common.russian_fio import TRussianFio
from declarations.management.commands.create_permalink_storage import CreatePermalinksStorageCommand

import declarations.models as models
import os
import json
from django.test import TestCase, tag


def build_declarator_squeeze(declarator_document_id, mapping_value, fio, income_main1, income_main2, use_only_surname,
                             person_ids_path):
    with open(person_ids_path, "w") as outp:
        fio_key = fio
        if use_only_surname:
            fio_dict = TRussianFio(fio)
            fio_key = fio_dict.family_name

        record = {
            build_section_passport(declarator_document_id, fio_key, income_main1): mapping_value,
            build_section_passport(declarator_document_id, fio_key, income_main2): mapping_value,
        }
        json.dump(record, outp, ensure_ascii=False, indent=4)


class CopyPersonIdTestCaseBase(TestCase):

    permalinks_folder = os.path.dirname(__file__)
    declarator_person_id = 178
    section_id1 = 1
    section_id2 = 2
    income_main1 = 12534
    income_main2 = 12535
    fio = "Иванов Иван Иванович"
    declarator_document_id = 1784

    def create_test_db(self):
        models.Section.objects.all().delete()
        models.Declarator_File_Reference.objects.all().delete()
        models.Source_Document.objects.all().delete()
        models.Person.objects.all().delete()
        self.assertGreater(models.Office.objects.count(), 0)

        src_doc = models.Source_Document(id=1)
        src_doc.save()

        models.Declarator_File_Reference(source_document=src_doc,
                                         declarator_document_id=self.declarator_document_id).save()

        section1 = models.Section(id=self.section_id1, source_document=src_doc, person_name=self.fio, office_id=1)
        section1.save()

        section2 = models.Section(id=self.section_id2, source_document=src_doc, person_name=self.fio, office_id=1)
        section2.save()

        models.Income(section=section1, size=self.income_main1, relative=models.Relative.main_declarant_code).save()
        models.Income(section=section2, size=self.income_main2, relative=models.Relative.main_declarant_code).save()

    def run_copy_person_id(self, use_only_surname, check_ambiguity, declarator_person_id=None):
        if declarator_person_id is None:
            declarator_person_id = self.declarator_person_id
        person_ids_path = os.path.join(os.path.dirname(__file__), "person_ids.json")
        mapping_value = "AMBIGUOUS_KEY" if check_ambiguity else declarator_person_id
        build_declarator_squeeze(self.declarator_document_id, mapping_value, self.fio,
                                 self.income_main1, self.income_main2,
                                 use_only_surname, person_ids_path)

        self.create_test_db()

        copier = CopyPersonIdCommand(None, None)

        copier.handle(None, read_person_from_json=person_ids_path,
                      permalinks_folder=CopyPersonIdTestCaseBase.permalinks_folder)


class Simple(CopyPersonIdTestCaseBase):
    @tag('central')
    def test(self):

        TPermaLinksPerson(CopyPersonIdTestCaseBase.permalinks_folder).create_and_save_empty_db()
        self.run_copy_person_id(False, False)

        self.assertEqual(models.Person.objects.count(), 1)
        section1 = models.Section.objects.get(id=self.section_id1)
        self.assertEqual(section1.person.declarator_person_id, self.declarator_person_id)
        self.assertEqual(section1.person.id, 1)


class OnlySurnameMatch(CopyPersonIdTestCaseBase):
    @tag('central')
    def test_(self):
        TPermaLinksPerson(CopyPersonIdTestCaseBase.permalinks_folder).create_and_save_empty_db()
        self.run_copy_person_id(True, False)
        self.assertEqual(models.Person.objects.count(), 1)
        section1 = models.Section.objects.get(id=self.section_id1)
        self.assertEqual(section1.person.declarator_person_id, self.declarator_person_id)
        self.assertEqual(section1.person.id, 1)


class Ambiguity(CopyPersonIdTestCaseBase):
    @tag('central')
    def test(self):
        TPermaLinksPerson(CopyPersonIdTestCaseBase.permalinks_folder).create_and_save_empty_db()

        self.run_copy_person_id(False, True)

        section1 = models.Section.objects.get(id=self.section_id1)
        self.assertEqual(section1.person, None)


class SimpleRememberPrimaryKeys(CopyPersonIdTestCaseBase):
    @tag('central')
    def test(self):
        TPermaLinksPerson(CopyPersonIdTestCaseBase.permalinks_folder).create_and_save_empty_db()
        self.run_copy_person_id(False, False)

        # check that we reuse old person ids
        CreatePermalinksStorageCommand(None, None).handle(None, directory=CopyPersonIdTestCaseBase.permalinks_folder)
        permalinks_db = TPermaLinksPerson(CopyPersonIdTestCaseBase.permalinks_folder)
        permalinks_db.open_db_read_only()
        permalinks_db.recreate_auto_increment_table()

        self.run_copy_person_id(False, False)
        self.assertEqual(permalinks_db.get_last_inserted_id_for_testing(), None)


class ChangeDeclaratorPersonId(CopyPersonIdTestCaseBase):
    @tag('central')
    def test(self):
        TPermaLinksPerson(CopyPersonIdTestCaseBase.permalinks_folder).create_and_save_empty_db()
        self.run_copy_person_id(False, False)

        # check that we reuse old person ids
        CreatePermalinksStorageCommand(None, None).handle(None, directory=CopyPersonIdTestCaseBase.permalinks_folder)
        permalinks_db = TPermaLinksPerson(CopyPersonIdTestCaseBase.permalinks_folder)
        permalinks_db.open_db_read_only()
        permalinks_db.recreate_auto_increment_table()

        new_declarator_person_id = self.declarator_person_id + 1
        self.run_copy_person_id(False, False, declarator_person_id=new_declarator_person_id)
        self.assertEqual(models.Person.objects.count(), 1)
        section1 = models.Section.objects.get(id=self.section_id1)
        self.assertEqual(section1.person.declarator_person_id, new_declarator_person_id)
        self.assertEqual(section1.person.id, 1)


class AddDeclaratorPersonIdWhileDisclosuresPersonAlreadyExists(CopyPersonIdTestCaseBase):
    @tag('central')
    def test(self):
        self.create_test_db()

        person_id = 1
        person = models.Person(id=person_id, person_name=self.fio)
        self.assertIsNone(person.declarator_person_id)
        person.save()

        section1 = models.Section.objects.get(id=self.section_id1)
        section1.person = person
        section1.save()

        TPermaLinksPerson(CopyPersonIdTestCaseBase.permalinks_folder).create_and_save_empty_db()

        CreatePermalinksStorageCommand(None, None).handle(None, directory=CopyPersonIdTestCaseBase.permalinks_folder)
        permalinks_db = TPermaLinksPerson(CopyPersonIdTestCaseBase.permalinks_folder)
        permalinks_db.open_db_read_only()
        permalinks_db.recreate_auto_increment_table()

        self.run_copy_person_id(False, False)
        self.assertEqual(models.Person.objects.count(), 1)
        section1 = models.Section.objects.get(id=self.section_id1)
        self.assertEqual(section1.person.declarator_person_id, self.declarator_person_id)
        self.assertEqual(section1.person.id, person_id)

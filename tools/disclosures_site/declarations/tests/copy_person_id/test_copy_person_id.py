from declarations.management.commands.permalinks import TPermaLinksDB
from declarations.management.commands.copy_person_id import CopyPersonIdCommand, build_section_passport
from declarations.russian_fio import TRussianFio
from declarations.management.commands.create_permalink_storage import CreatePermalinksStorageCommand

import declarations.models as models
import os
import json
from django.test import TestCase


class CopyPersonIdTestCaseBase(TestCase):

    def check_case(self, use_only_surname, check_ambiguity, permalinks_path=None):
        models.Section.objects.all().delete()
        models.Declarator_File_Reference.objects.all().delete()
        models.Source_Document.objects.all().delete()
        models.Person.objects.all().delete()
        self.assertGreater(models.Office.objects.count(), 0)

        fio = "Иванов Иван Иванович"
        document_id = 1784
        income_main1 = 12534
        income_main2 = 12535
        declarator_person_id = 178
        person_ids_path = os.path.join(os.path.dirname(__file__), "person_ids.json")
        with open(person_ids_path, "w") as outp:
            fio_key = fio
            if use_only_surname:
                fio_dict = TRussianFio(fio)
                fio_key = fio_dict.family_name

            value = declarator_person_id
            if check_ambiguity:
                value = "AMBIGUOUS_KEY"
            record = {
                build_section_passport(document_id, fio_key, income_main1): value,
                build_section_passport(document_id, fio_key, income_main2): value,
            }
            json.dump(record, outp, ensure_ascii=False, indent=4)

        src_doc = models.Source_Document(id=1)
        src_doc.office_id = 1
        src_doc.save()

        models.Declarator_File_Reference(source_document=src_doc, declarator_document_id=document_id).save()

        section1 = models.Section(id=1, source_document=src_doc, person_name=fio)
        section1.save()

        section2 = models.Section(id=2, source_document=src_doc, person_name=fio)
        section2.save()

        models.Income(section=section1, size=income_main1, relative=models.Relative.main_declarant_code).save()
        models.Income(section=section2, size=income_main2, relative=models.Relative.main_declarant_code).save()

        if permalinks_path is None:
            permalinks_path = os.path.join(os.path.dirname(__file__), "permalinks.dbm")
            TPermaLinksDB(permalinks_path).create_and_save_empty_db()

        copier = CopyPersonIdCommand(None, None)
        copier.handle(None, read_person_from_json=person_ids_path, permanent_links_db=permalinks_path)

        section1.refresh_from_db()
        if check_ambiguity:
            self.assertEqual(section1.person, None)
        else:
            self.assertEqual(models.Person.objects.count(), 1)
            #primary_key_db = TPermaLinksDB(permalinks_path)
            #self.assertEqual(primary_key_db.get_new_max_id(models.Person), 1)
            self.assertEqual(section1.person.declarator_person_id, declarator_person_id)
            self.assertEqual(section1.person.id, 1)


class Simple(CopyPersonIdTestCaseBase):
    def test(self):
        self.check_case(False, False)


class OnlySurnameMatch(CopyPersonIdTestCaseBase):
    def test_(self):
        self.check_case(True, False)


class Ambiguity(CopyPersonIdTestCaseBase):
    def test(self):
        self.check_case(False, True)


class SimpleRememberPrimaryKeys(CopyPersonIdTestCaseBase):
    def test(self):
        self.check_case(False, False)

        # check that we reuse old person ids
        permalinks_path = os.path.join(os.path.dirname(__file__), "permalinks.dbm")
        CreatePermalinksStorageCommand(None, None).handle(None, output_dbm_file=permalinks_path)
        permalinks_db = TPermaLinksDB(permalinks_path)
        permalinks_db.open_db_read_only()
        permalinks_db.create_sql_sequences()

        self.check_case(False, False, permalinks_path=permalinks_path)
        self.assertEqual(permalinks_db.get_new_max_id(models.Person), None)
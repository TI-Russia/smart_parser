from declarations.management.commands.copy_person_id import CopyPersonIdCommand, build_section_passport
import declarations.models as models
import os
import json
from declarations.management.commands.permalinks import TPermaLinksDB
from django.test import TransactionTestCase
from django.test import TestCase


class CopyPersonIdTestCaseBase(TestCase):

    def check_case(self, use_only_surname, check_ambiguity):
        models.Section.objects.all().delete()
        self.assertGreater(models.Office.objects.count(), 0)

        fio = "Иванов Иван Иванович"
        document_id = 1784
        income_main = 12534
        declarator_person_id = 178
        person_ids_path = os.path.join(os.path.dirname(__file__), "person_ids.json")
        with open(person_ids_path, "w") as outp:
            fio_key = fio
            if use_only_surname:
                fio_key = fio.split()[0]
            value = declarator_person_id
            if check_ambiguity:
                value = "AMBIGUOUS_KEY"
            record = {
                build_section_passport(document_id, fio_key, income_main): value
            }
            json.dump(record, outp, ensure_ascii=False, indent=4)
        src_doc = models.Source_Document()
        src_doc.office_id = 1
        src_doc.id = 1
        src_doc.save()

        decl_info = models.Declarator_File_Reference(source_document=src_doc,
                                                     declarator_document_id=document_id)
        decl_info.save()

        section = models.Section(source_document=src_doc,
                                 person_name=fio)
        section.id = 1
        section.save()

        income = models.Income(section=section,
                               size=income_main,
                               relative=models.Relative.main_declarant_code
                               )
        income.save()

        permalinks_path = os.path.join(os.path.dirname(__file__), "permalinks.dbm")
        p = TPermaLinksDB(permalinks_path)
        p.create_db()
        p.close_db()

        copier = CopyPersonIdCommand(None, None)
        copier.handle(None, read_person_from_json=person_ids_path, permanent_links_db=permalinks_path)

        section.refresh_from_db()
        if check_ambiguity:
            self.assertEqual(section.person, None)
        else:
            self.assertEqual(section.person.declarator_person_id, declarator_person_id)


class Simple(CopyPersonIdTestCaseBase):
    def test(self):
        self.check_case(False, False)


class OnlySurnameMatch(CopyPersonIdTestCaseBase):
    def test_(self):
        self.check_case(True, False)


class Ambiguity(CopyPersonIdTestCaseBase):
    def test(self):
        self.check_case(False, True)


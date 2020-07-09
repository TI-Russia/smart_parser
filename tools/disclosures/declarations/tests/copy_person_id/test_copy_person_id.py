from django.test import TestCase
from declarations.management.commands.copy_person_id import CopyPersonIdCommand, build_key
import declarations.models as models
import os
import json


class CopyPersonIdTestCase(TestCase):
    def setUp(self):
        pass

    def check_case(self, use_only_surname, check_ambiguity):
        fio = "Иванов Иван Иванович"
        document_id = 178
        income_main = 12534
        person_id = 178
        person_ids_path = os.path.join(os.path.dirname(__file__), "person_ids.json")
        with open(person_ids_path, "w") as outp:
            fio_key = fio
            if use_only_surname:
                fio_key = fio.split()[0]
            value = person_id
            if check_ambiguity:
                value = "AMBIGUOUS_KEY"
            record = {
                build_key(document_id, fio_key, income_main): value
            }
            json.dump(record, outp)

        office = models.Office()
        office.save()

        src_doc = models.Source_Document(office=office)
        src_doc.save()

        decl_info = models.Declarator_File_Info(source_document=src_doc,
                                                declarator_document_id=person_id)
        decl_info.save()

        models.Section.objects.all().delete()
        section = models.Section(source_document=src_doc,
                                 person_name=fio)
        section.save()

        income = models.Income(section=section,
                               size=income_main,
                               relative=models.Relative.main_declarant_code
                               )
        income.save()

        importer = CopyPersonIdCommand(None, None)

        importer.handle(None, read_person_from_json=person_ids_path)
        section.refresh_from_db()
        if check_ambiguity:
            self.assertEqual(section.person, None)
        else:
            self.assertEqual(section.person.id, person_id)

    def test_simple_import(self):
        self.check_case(False, False)

    def test_only_surname_match(self):
        self.check_case(True, False)

    def test_ambiguity(self):
        self.check_case(False, True)
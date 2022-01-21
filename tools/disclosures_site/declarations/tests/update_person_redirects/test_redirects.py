from declarations.management.commands.create_database import CreateDatabase
from declarations.management.commands.update_person_redirects import UpdatePersonRedirects
import declarations.models as models
from office_db.offices_in_memory import TOfficeTableInMemory
from django.test import TestCase, tag
from django.db import connection
from django.conf import settings
import argparse
import os
import json

TEST_OFFICE_ID = 1697


def check_database_exists(database_name):
    with connection.cursor() as cursor:
        res = cursor.execute("SHOW DATABASES LIKE '{}'".format(database_name))
        return res > 0


class PersonRedirectTestCase(TestCase):
    tmp_prod_database_name = "tmp_redirect_db"

    @classmethod
    def setUpClass(cls):
        TOfficeTableInMemory.SELECTED_OFFICES_FOR_TESTS = set([TEST_OFFICE_ID])
        create_db = CreateDatabase(None, None)
        parser = argparse.ArgumentParser()
        create_db.add_arguments(parser)
        args = parser.parse_args([])
        args.database_name = PersonRedirectTestCase.tmp_prod_database_name
        create_db.handle(None, **args.__dict__)
        TOfficeTableInMemory.SELECTED_OFFICES_FOR_TESTS = None

    @classmethod
    def tearDownClass(cls):
        pass

    def _fixture_teardown(self):
        self.create_records({})
        pass

    def create_records(self, records):
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()
        models.Person.objects.all().delete()
        models.PersonRedirect.objects.all().delete()
        assert models.Office.objects.all().count() > 0
        for d in records.get('source_documents', []):
            d = models.Source_Document(**d)
            d.save()

        for d in records.get('persons', []):
            models.Person(**d).save()

        for d in records.get('sections', []):
            if len(models.Office.objects.filter(id=d['office_id'])) == 0:
                o = models.Office(id=d['office_id'], name="aaa")
                o.save()
            models.Section(**d).save()

        for d in records.get('redirects', []):
            models.PersonRedirect(**d).save()

    def fill_old_data(self, data):
        save_db_name = settings.DATABASES['default']['NAME']
        settings.DATABASES['default']['NAME'] = self.tmp_prod_database_name
        connection.connect()
        self.create_records(data)
        settings.DATABASES['default']['NAME'] = save_db_name
        connection.connect()

    def run_updater(self, input_squeeze):
        updater = UpdatePersonRedirects(None, None)
        parser = argparse.ArgumentParser()
        updater.add_arguments(parser)
        args = parser.parse_args([])
        args.prod_database_name = self.tmp_prod_database_name
        args.input_access_log_squeeze = os.path.join(os.path.dirname(__file__), "access_log_squeeze.txt")
        args.output_access_log_squeeze = os.path.join(os.path.dirname(__file__), "access_log_squeeze.txt.out")
        if os.path.exists(args.output_access_log_squeeze):
            os.unlink(args.output_access_log_squeeze)
        with open(args.input_access_log_squeeze, "w") as outp:
            for s in input_squeeze:
                outp.write(json.dumps(s) + "\n")

        updater.handle(None, **args.__dict__)
        output_squeeze = list()
        with open(args.output_access_log_squeeze) as inp:
            lines = inp.readlines()
            for l in lines:
                output_squeeze.append(json.loads(l))
        return output_squeeze

    @tag('front')
    def test_missing_person(self):
        old_data = {
            'persons': [{'id': 1}],
            'source_documents': [{'id': 1}],
            'sections': [{'id': 1, 'person_id': 1, 'source_document_id': 1, 'office_id': 1}]
        }
        self.fill_old_data(old_data)
        self.create_records({})
        input_squeeze = [{"record_id": 1, "record_type": "person", "req_freq": 1}]
        output_squeeze = self.run_updater(input_squeeze)
        self.assertEqual(0, len(output_squeeze))

    @tag('front')
    def test_copy_old_redirects(self):
        data = {
            'persons': [{'id': 1}],
            'source_documents': [{'id': 1}],
            'sections': [{'id': 1, 'person_id': 1, 'source_document_id': 1, 'office_id': 1}],
            'redirects': [{'id': 2, 'new_person_id': 1}]
        }
        self.fill_old_data(data)
        del data['redirects']
        self.create_records(data)
        input_squeeze = [{"record_id": 1, "record_type": "person", "req_freq": 1}]
        output_squeeze = self.run_updater(input_squeeze)
        self.assertEqual(1, len(output_squeeze))
        self.assertEqual(1, output_squeeze[0]['record_id'])

        self.assertEqual(1, models.PersonRedirect.objects.all().count())
        self.assertEqual(1, models.PersonRedirect.objects.get(id=2).new_person_id)

    @tag('front')
    def test_create_redirect(self):
        data = {
            'persons': [{'id': 1}],
            'source_documents': [{'id': 1}],
            'sections': [{'id': 1, 'person_id': 1, 'source_document_id': 1, 'office_id': 1}],
        }
        self.fill_old_data(data)

        data = {
            'persons': [{'id': 2}],
            'source_documents': [{'id': 1}],
            'sections': [{'id': 1, 'person_id': 2, 'source_document_id': 1, 'office_id': 1}],
        }
        self.create_records(data)

        input_squeeze = [{"record_id": 1, "record_type": "person", "req_freq": 1}]
        output_squeeze = self.run_updater(input_squeeze)
        self.assertEqual(1, len(output_squeeze))
        self.assertEqual(2, output_squeeze[0]['record_id'])

        self.assertEqual(1, models.PersonRedirect.objects.all().count())
        r = models.PersonRedirect.objects.get(id=1)
        self.assertIsNotNone(r)
        self.assertEqual(2, r.new_person_id)

    @tag('front')
    def test_create_redirect_of_redirect(self):
        data = {
            'persons': [{'id': 2}],
            'source_documents': [{'id': 1}],
            'sections': [{'id': 1, 'person_id': 2, 'source_document_id': 1, 'office_id': 1}],
            'redirects': [{'id': 1, 'new_person_id': 2}]
        }
        self.fill_old_data(data)

        data = {
            'persons': [{'id': 3}],
            'source_documents': [{'id': 1}],
            'sections': [{'id': 1, 'person_id': 3, 'source_document_id': 1, 'office_id': 1}],
        }
        self.create_records(data)

        input_squeeze = [{"record_id": 1, "record_type": "person", "req_freq": 1}]
        output_squeeze = self.run_updater(input_squeeze)
        self.assertEqual(1, len(output_squeeze))
        self.assertEqual(3, output_squeeze[0]['record_id'])

        self.assertEqual(2, models.PersonRedirect.objects.all().count())
        r = models.PersonRedirect.objects.get(id=1)
        self.assertIsNotNone(r)
        self.assertEqual(2, r.new_person_id)

        r = models.PersonRedirect.objects.get(id=2)
        self.assertIsNotNone(r)
        self.assertEqual(3, r.new_person_id)

    @tag('front')
    def test_forget_section(self):
        data = {
            'source_documents': [{'id': 1}],
            'sections': [{'id': 1, 'source_document_id': 1, 'office_id': 1}],
        }
        self.fill_old_data(data)

        data = {
            'persons': [{'id': 3}],
            'source_documents': [{'id': 1}],
            'sections': [{'id': 2, 'source_document_id': 1, 'office_id': 1}],
        }
        self.create_records(data)

        input_squeeze = [{"record_id": 1, "record_type": "section", "req_freq": 1}]
        output_squeeze = self.run_updater(input_squeeze)
        self.assertEqual(0, len(output_squeeze))

    @tag('front')
    def test_redirect_to_best_person(self):
        assert models.Office.objects.get(id=1) is not None
        data = {
            'persons': [{'id': 1}],
            'source_documents': [{'id': 1}],
            'sections': [{'id': 1, 'person_id': 1, 'source_document_id': 1, 'office_id': 1}],
            'sections': [{'id': 2, 'person_id': 1, 'source_document_id': 1, 'office_id': 1}],
            'sections': [{'id': 3, 'person_id': 1, 'source_document_id': 1, 'office_id': 1}],
        }
        self.fill_old_data(data)

        data = {
            'persons': [{'id': 2}],
            'persons': [{'id': 3}],
            'source_documents': [{'id': 1}],
            'sections': [{'id': 1, 'person_id': 2, 'source_document_id': 1, 'office_id': 1}],
            'sections': [{'id': 2, 'person_id': 3, 'source_document_id': 1, 'office_id': 1}],
            'sections': [{'id': 3, 'person_id': 3, 'source_document_id': 1, 'office_id': 1}],
        }
        self.create_records(data)

        input_squeeze = [{"record_id": 1, "record_type": "person", "req_freq": 1}]
        output_squeeze = self.run_updater(input_squeeze)
        self.assertEqual(1, len(output_squeeze))
        self.assertEqual(3, output_squeeze[0]['record_id'])

        self.assertEqual(1, models.PersonRedirect.objects.all().count())
        r = models.PersonRedirect.objects.get(id=1)
        self.assertIsNotNone(r)
        self.assertEqual(3, r.new_person_id)


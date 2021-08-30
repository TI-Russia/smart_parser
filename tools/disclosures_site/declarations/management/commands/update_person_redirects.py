from common.logging_wrapper import setup_logging
import declarations.models as models

from django.core.management import BaseCommand
from django.db import connection
from disclosures.settings.common import DATABASES
import pymysql
from collections import defaultdict
import json


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(log_file_name="update_person_redirects.log")
        self.options = None
        self.old_person_to_sections = defaultdict(list)
        self.redirects = dict()
        self.new_section_to_person = dict()

    def add_arguments(self, parser):
        parser.add_argument(
            '--prod-database-name',
            dest='prod_database_name',
            default="disclosures_db"
        )
        parser.add_argument(
            '--prod-database-user',
            dest='prod_database_user',
            default=DATABASES['default']['USER']
        )
        parser.add_argument(
            '--prod-database-password',
            dest='prod_database_password',
            default=DATABASES['default']['PASSWORD']
        )
        parser.add_argument(
            '--input-access-log-squeeze',
            dest='input_access_log_squeeze',
        )
        parser.add_argument(
            '--output-access-log-squeeze',
            dest='output_access_log_squeeze',
        )

    def init_prod_connection(self):
        return pymysql.connect(db=self.options['prod_database_name'],
                               user=self.options['prod_database_user'],
                               password=self.options['prod_database_password'],
                               unix_socket="/var/run/mysqld/mysqld.sock")

    def read_old_person_to_sectiom_mapping(self):
        db = self.init_prod_connection()
        query = """
                    select id, person_id
                    from declarations_section
                    where person_id is not null
                """
        cursor = db.cursor()
        cursor.execute(query)
        self.old_person_to_sections.clear()
        for section_id, person_id in cursor:
            self.old_person_to_sections[person_id].append(section_id)
        cursor.close()
        db.close()
        self.logger.info("built old person->sections for {} persons ".format(len(self.old_person_to_sections)))

    def read_new_section_to_person_mapping(self):
        query = """
                    select id, person_id
                    from declarations_section
                    where person_id is not null
                """
        self.new_section_to_person.clear()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for section_id, person_id in cursor:
                self.new_section_to_person[section_id] = person_id
        self.logger.info("built new section->person mapping for {} sections ".format(len(self.new_section_to_person)))

    def read_old_redirects(self):
        db = self.init_prod_connection()
        query = """
                    select id, new_person_id
                    from declarations_personredirect
                """
        cursor = db.cursor()
        cursor.execute(query)
        self.redirects.clear()
        models.PersonRedirect.objects.all().delete()
        for old_person_id, new_person_id in cursor:
            self.redirects[old_person_id] = new_person_id
            models.PersonRedirect(id=old_person_id, new_person_id=new_person_id).save()
        cursor.close()
        db.close()
        self.logger.info("found {} redirects in old (prod) database ".format(len(self.redirects)))

    def person_exists(self, person_id):
        try:
            return models.Person.objects.get(id=person_id) is not None
        except models.Person.DoesNotExist as exp:
            return False

    def try_to_make_redirect(self, person_id):
        already_redirect = self.redirects.get(person_id)
        if already_redirect is not None:
            if self.person_exists(already_redirect):
                return already_redirect
            else:
                # it was redirected to X in the old db, but x is missing in the new db, try to calc a new target
                person_id = already_redirect
        assert person_id in self.old_person_to_sections
        max_persons = defaultdict(int)
        for section_id in self.old_person_to_sections.get(person_id, list()):
            new_person_id = self.new_section_to_person.get(section_id)
            if new_person_id is not None:
                max_persons[new_person_id] += 1
        if len(max_persons) == 0:
            return None
        new_person_id = max(max_persons.items(), key=lambda x: x[1])[0]
        redirect = models.PersonRedirect(id=person_id, new_person_id=new_person_id)
        redirect.save()
        return new_person_id

    def read_access_log_squeeze(self):
        with open(self.options['input_access_log_squeeze']) as inp:
            for line in inp:
                line = line.strip()
                request = json.loads(line)
                if request['record_type'] == 'section':
                    if request['record_id'] not in self.new_section_to_person:
                        self.logger.error("access log record {} is missing in the db, users are angry!".format(line))
                    else:
                        yield line
                elif self.person_exists(request['record_id']):
                    yield line
                else:
                    new_person_id = self.try_to_make_redirect(request['record_id'])
                    if new_person_id is not None:
                        request['record_id'] = new_person_id
                        yield json.dumps(request)
                    else:
                        self.logger.error("cannot create redirect for {}".format(line.strip()))

    def filter_access_log_squeeze(self):
        with open(self.options['output_access_log_squeeze'], "w") as outp:
            for l in self.read_access_log_squeeze():
                outp.write(l + "\n")

    def handle(self, *args, **options):
        self.options = options
        self.read_old_person_to_sectiom_mapping()
        self.read_old_redirects()
        self.read_new_section_to_person_mapping()
        self.filter_access_log_squeeze()

UpdatePersonRedirects=Command
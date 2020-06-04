from django.core.management import BaseCommand
import declarations.models as models
import pymysql
import sys
from declarations.serializers import TSectionPassportFactory

def copy_human_merges(human_persons):
    mergings_count = 0
    sys.stdout.write("set person_id to sections\n")
    cnt = 0
    for section_id, factory in TSectionPassportFactory.get_all_passport_factories():
        cnt += 1
        if (cnt % 10000) == 0:
            sys.stdout.write(".")
        person_id = factory.search_by_passports(human_persons)[0]
        if person_id is not None:
            person = models.Person.objects.get_or_create(id=person_id)[0]
            section = models.Section.objects.get(id=section_id)

            person.declarator_person_id = person_id
            if person.person_name is None or len(person.person_name) < len(section.person_name):
                person.person_name = section.person_name
            person.save()

            section.person = person
            section.save()
            mergings_count += 1
    sys.stdout.write("\nset human person id to {} records\n".format(mergings_count))


class Command(BaseCommand):
    help = 'copy person id from declarator to disclosures'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

    def handle(self, *args, **options):
        db_connection = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                                        unix_socket="/var/run/mysqld/mysqld.sock")
        factories = TSectionPassportFactory.get_all_passports_from_declarator_with_person_id(db_connection)
        human_persons = TSectionPassportFactory.get_all_passports_dict(factories)
        db_connection.close()
        copy_human_merges(human_persons)

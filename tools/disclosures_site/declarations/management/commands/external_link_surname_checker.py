import declarations.models as models
from django.core.management import BaseCommand
from common.logging_wrapper import setup_logging
import json


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(logger_name='external_link')

    def add_arguments(self, parser):
        parser.add_argument(
            '--links-input-file',
            dest='input_links'
        )

    def handle(self, *args, **options):
        with open (options['input_links']) as inp:
            links = json.load(inp)
        link_count = 0
        for link in links:
            person_id = link['person_id']
            surname = link['fio'].split()[0].lower()
            try:
                person = models.Person.objects.get(id=person_id)
            except models.Person.DoesNotExist:
                raise Exception("cannot find person id={}".format(person_id))
            if not person.person_name.lower().startswith(surname):
                raise Exception("person id={} surname check failed ({} != {})".format(person_id, person.person_name, surname))
            link_count += 1
        self.logger.info("checked {} person surnames".format(link_count))
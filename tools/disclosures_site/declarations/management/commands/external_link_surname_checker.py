import declarations.models as models
from django.core.management import BaseCommand
from common.logging_wrapper import setup_logging
import json


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(logger_name='external_link')
        self.options = None
        self.errors_count = 0

    def add_arguments(self, parser):
        parser.add_argument(
            '--links-input-file', dest='input_links'
        )
        parser.add_argument(
            '--fail-fast', dest='fail_fast', action="store_true", default=False
        )

    def print_error(self, msg):
        if self.options.get('fail_fast', False):
            raise Exception(msg)
        else:
            self.logger.error(msg)
            self.errors_count += 1

    def handle(self, *args, **options):
        self.options = options
        with open (options['input_links']) as inp:
            links = json.load(inp)
        link_count = 0
        for link in links:
            person_id = link['person_id']
            surname = link['fio'].split()[0].lower()
            try:
                person = models.Person.objects.get(id=person_id)
            except models.Person.DoesNotExist:
                self.print_error("cannot find person id={}".format(person_id))
                continue
            if not person.person_name.lower().startswith(surname):
                self.print_error("person id={} surname check failed ({} != {})".format(person_id, person.person_name, surname))
                continue
            link_count += 1
        self.logger.info("checked {} person surnames".format(link_count))
        if self.errors_count > 0:
            raise Exception("there are {} errors in this db while running {}, see log file for details".format(self.errors_count, __file__))
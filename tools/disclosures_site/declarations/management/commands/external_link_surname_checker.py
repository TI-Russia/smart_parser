import declarations.models as models
from django.core.management import BaseCommand
from common.logging_wrapper import setup_logging


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(logger_name='external_link')

    def add_arguments(self, parser):
        parser.add_argument(
            '--input-links-file',
            dest='input_links'
        )

    def handle(self, *args, **options):
        pass
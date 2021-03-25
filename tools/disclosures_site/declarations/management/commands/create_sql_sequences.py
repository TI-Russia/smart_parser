from django.core.management import BaseCommand
from declarations.permalinks import TPermalinksManager
from common.logging_wrapper import setup_logging


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        TPermalinksManager.add_arguments(parser)

    def handle(self, *args, **options):
        logger = setup_logging(logger_name="create_sql_sequences")
        TPermalinksManager(logger, options).create_sql_sequences()

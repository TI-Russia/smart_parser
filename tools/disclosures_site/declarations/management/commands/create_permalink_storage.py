from declarations.permalinks import TPermalinksManager
from common.logging_wrapper import setup_logging
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'create permalink storage (in gnu.dmb format) to make web links almost permanent'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

    def add_arguments(self, parser):
        TPermalinksManager.add_arguments(parser)

    def handle(self, *args, **options):
        logger = setup_logging(logger_name="create_permalink_storage")
        TPermalinksManager(logger, options).create_permalinks()
        logger.info("all done")

CreatePermalinksStorageCommand=Command

from django.core.management import BaseCommand
from django.conf import settings
import pymysql
import sys
from declarations.management.commands.permalinks import TPermaLinksDB


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            '--permanent-links-db',
            dest='permanent_links_db',
            required=True
        )

    def handle(self, *args, **options):
        self.primary_keys_builder = TPermaLinksDB(self.options['permanent_links_db'])
        self.primary_keys_builder.open_db_read_only()
        self.primary_keys_builder.create_sql_sequences()

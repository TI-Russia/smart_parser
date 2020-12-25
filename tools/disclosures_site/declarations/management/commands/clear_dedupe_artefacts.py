from django.core.management import BaseCommand
from django.db import connection
import sys
from declarations.management.commands.permalinks import TPermaLinksDB
import declarations.models as models


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
                '--delete-all',
            dest='delete_all',
            default=False,
            action="store_true",
            help='delete also human mergings'
        )
        parser.add_argument(
            '--permanent-links-db',
            dest='permanent_links_db',
            required=False
        )

    def run_sql(self, cursor, cmd):
        sys.stdout.write(cmd + "\n")
        cursor.execute(cmd)

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            self.run_sql(cursor, "SET FOREIGN_KEY_CHECKS = 0;")
            if options.get('delete_all', False):
                self.run_sql(cursor, "update declarations_section set person_id=null, dedupe_score=null;")
                self.run_sql(cursor, "truncate table declarations_person;")
            else:
                primary_keys_builder = TPermaLinksDB(options['permanent_links_db'])
                primary_keys_builder.open_db_read_only()
                primary_keys_builder.recreate_auto_increment_table(models.Person)
                sys.stdout.write("person count = {}\n".format(models.Person.objects.count()))
                self.run_sql(cursor, "delete from declarations_person where id in (select person_id from declarations_section where dedupe_score > 0)")
                sys.stdout.write("person count = {}\n".format( models.Person.objects.count()))
                self.run_sql(cursor, "update declarations_section set person_id=null where dedupe_score > 0;")
                self.run_sql(cursor, "update declarations_section set dedupe_score = 0;")

                primary_keys_builder = TPermaLinksDB(options['permanent_links_db'])
                primary_keys_builder.update_person_records_count_and_close()
            self.run_sql(cursor, "SET FOREIGN_KEY_CHECKS = 1;")

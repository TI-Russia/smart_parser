from django.core.management import BaseCommand
from django.db import connection
import sys


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def run_sql(self, cursor, cmd):
        sys.stdout.write(cmd + "\n")
        cursor.execute(cmd)

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            self.run_sql(cursor, "SET FOREIGN_KEY_CHECKS = 0;")
            self.run_sql(cursor, "update declarations_section set person_id=null, dedupe_score=null;")
            self.run_sql(cursor, "truncate table declarations_person;")
            self.run_sql(cursor, "SET FOREIGN_KEY_CHECKS = 1;")

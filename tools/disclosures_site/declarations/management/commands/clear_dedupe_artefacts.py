from django.core.management import BaseCommand
from django.db import connection


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cursor.execute("""
               delete from declarations_person 
               where id in (select person_id from declarations_section where dedupe_score > 0)
               """);
            cursor.execute("update declarations_section set person_id=null where dedupe_score > 0;")
            cursor.execute("update declarations_section set dedupe_score = 0;")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

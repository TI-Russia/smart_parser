import declarations.models as models
from django.core.management import BaseCommand
from django.db import connection
import sys

class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            for m in [models.Income, models.RealEstate, models.Vehicle, models.Section, models.Declarator_File_Reference,
                      models.Web_Reference, models.Source_Document, models.Person]:
                table_name = m.objects.model._meta.db_table
                cmd = "truncate table {};".format(table_name)
                sys.stdout.write(cmd + "\n")
                cursor.execute(cmd)
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

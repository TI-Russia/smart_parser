#this script is not used, because we use binary deployng. Delete it in 2022 year

from django.core.management import BaseCommand
from django.conf import settings
import pymysql
import sys
import os


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
                '--host',
            dest='host',
            required=False,
            default="localhost",
        )
        parser.add_argument(
                '--username',
            dest='username',
            required=False,
            default="root",
            help="mysql user name that can create db, default  root",
        )
        parser.add_argument(
                '--password',
            dest='password',
            required=False,
            help="mysql root password",
            default="root"
        )

        parser.add_argument(
                '--input-folder',
            dest='input_folder',
            required=True,
        )

    def run_sql(self, cursor, cmd):
        sys.stdout.write(cmd + "\n")
        cursor.execute(cmd)

    def check_database_exists(self, cursor, database_name):
        res = cursor.execute("SHOW DATABASES LIKE '{}'".format(database_name))
        return res > 0

    def handle(self, *args, **options):
        db_connection = pymysql.connect(
            user=options.get('username'),
            password=options.get('password'),
            )
        if db_connection is None:
            sys.stdout.write("cannot make local connection to the database\n")
        else:
            database_name = settings.DATABASES['default']['NAME']
            with db_connection.cursor() as cursor:
                assert (self.check_database_exists(cursor, database_name))
                self.run_sql(cursor, "SET FOREIGN_KEY_CHECKS=0;")
                self.run_sql(cursor, "use {};".format(database_name))

                for table_name in ["person", "source_document", "section", "declarator_file_reference", "web_reference", \
                    "person_rating", "person_rating_items", "realestate", "vehicle", "income"]:
                    table_name = "declarations_" + table_name
                    file_path = os.path.join(options.get('input_folder'), table_name + ".txt")
                    assert os.path.exists (file_path)
                    self.run_sql(cursor, "LOAD DATA INFILE '{}' "
                                         "INTO TABLE {} ; ".format(
                                file_path, table_name))
                db_connection.close()
            sys.stdout.write("check_connection ...\n")

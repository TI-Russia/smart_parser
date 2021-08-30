import os

from django.core import management
from django.core.management import BaseCommand
from django.conf import settings
import pymysql
import sys
from django.db import connection as django_connection


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
            default="db_creator",
            help="mysql user name that can create db, default  db_creator",
        )
        parser.add_argument(
                '--database-name',
            dest='database_name',
            default=settings.DATABASES['default']['NAME']
        )
        parser.add_argument(
                '--password',
            dest='password',
            required=False,
            help="mysql root password, default read from environment variable DB_CREATOR_PASSWORD",
            default=os.environ.get('DB_CREATOR_PASSWORD')
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
            database_name = options['database_name']
            disclosures_user = settings.DATABASES['default']['USER']
            disclosures_password = settings.DATABASES['default']['PASSWORD']
            with db_connection.cursor() as cursor:
                if self.check_database_exists(cursor, database_name):
                    sys.stdout.write("recreate database {}\n".format(database_name))
                else:
                    sys.stdout.write("create new database {}\n".format(database_name))

                self.run_sql(cursor, "drop database if exists {};".format(database_name))
                self.run_sql(cursor, "drop database if exists test_{}".format(database_name))
                self.run_sql(cursor, "create database {} character set utf8mb4 collate utf8mb4_unicode_ci;".format(database_name))
                self.run_sql(cursor, "create user if not exists '{}'@ identified by '{}';".format(
                    disclosures_user, disclosures_password))
                self.run_sql(cursor,
                    "GRANT ALL PRIVILEGES ON {}.* TO '{}'@".format(database_name, disclosures_user))
                db_connection.close()

                save_db_name = settings.DATABASES['default']['NAME']

                settings.DATABASES['default']['NAME'] = database_name
                django_connection.connect()

                management.call_command('makemigrations')
                management.call_command('migrate')

                settings.DATABASES['default']['NAME'] = save_db_name
                django_connection.connect()
                #connection = save_connection

CreateDatabase=Command
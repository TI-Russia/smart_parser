from django.core.management import BaseCommand
from django.conf import settings
import pymysql
import sys


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
                '--username',
            dest='username',
            required=False,
            default="root",
            help="mysql user name, default  root",
        )
        parser.add_argument(
                '--password',
            dest='password',
            required=True,
            help="mysql root password"
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
            unix_socket = "/var/run/mysqld/mysqld.sock")
        if db_connection is None:
            sys.stdout.write("cannot make local connection to the database\n")
        else:
            database_name = settings.DATABASES['default']['NAME']
            disclosures_user = settings.DATABASES['default']['USER']
            disclosures_password = settings.DATABASES['default']['PASSWORD']
            with db_connection.cursor() as cursor:
                if self.check_database_exists(cursor, database_name):
                    answer = input("delete database {} (yes, no)? ".format(database_name))
                    if answer != "yes":
                        return
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
            sys.stdout.write("check_connection ...\n")
            db_connection = pymysql.connect(
                user=disclosures_user,
                password=disclosures_password,
                unix_socket="/var/run/mysqld/mysqld.sock")
            if db_connection is None:
                sys.stdout.write("cannot connect using username={}, password={}\n".format(disclosures_user, disclosures_password))
            else:
                sys.stdout.write("connected\n")

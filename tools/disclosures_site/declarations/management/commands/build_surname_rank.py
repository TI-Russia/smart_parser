import declarations.models as models
from django.core.management import BaseCommand
import logging
import os
import sys
from collections import defaultdict
from declarations.common import resolve_fullname
from django.conf import settings


def setup_logging(logfilename="surname_rank.log"):
    logger = logging.getLogger("surname_rank")
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    return logger


class Command(BaseCommand):
    help = 'create rubric for offices'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging()

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            dest='verbose',
            type=int,
            help='set verbosity, default is DEBUG',
            default=0
        )

    def get_surname_and_name(self, person_name):
        fio = resolve_fullname(person_name)
        if fio is None:
            return None, None
        surname = fio['family_name'].lower()
        name = "{} {}".format(fio.get('name', " ")[0].lower(), fio.get('patronymic', " ")[0].lower())
        return surname, name

    def build_dicts(self):
        surname_to_name = defaultdict(set)
        name_to_surname = defaultdict(set)
        self.logger.info("read sections")
        cnt = 0
        all_ids = list()
        for s in models.Section.objects.raw("select id, person_name from declarations_section"):
            surname, name = self.get_surname_and_name(s.person_name)
            if surname is not None:
                all_ids.append((s.id, surname, name))
                surname_to_name[surname].add(name)
                name_to_surname[name].add(surname)
                cnt += 1
                #if cnt > 10000:
                #    break
        self.logger.info("processed {} sections".format(cnt))

        surname_rank_list = sorted(((len(v), k) for k, v in surname_to_name.items()), reverse=True)
        surname_rank_dict = dict((surname, surname_rank) for surname_rank, (freq, surname) in enumerate(surname_rank_list))
        self.logger.info("len(surname_rank_dict) = {}".format(len(surname_rank_dict)))

        name_rank_list = sorted(((len(v), k) for k, v in name_to_surname.items()), reverse=True)
        name_rank_dict = dict(
            (name, name_rank) for name_rank, (freq, name) in enumerate(name_rank_list))
        self.logger.info("len(name_rank_dict) = {}".format(len(name_rank_dict)))
        return surname_rank_dict, name_rank_dict, all_ids

    def write_temp_file(self, all_ids, surname_rank_dict, name_rank_dict, temp_path):
        self.logger.info("create temp file {}".format(temp_path))
        with open(temp_path, "w") as outp:
            outp.write("""
                create temporary table tmp_surname_rank (
                      `id` int,
                      `surname_rank` int,
                      `name_rank` int);
                """)
            index = 0
            for id, surname, name in all_ids:
                if index % 10000 == 0:
                    if index > 0:
                        outp.write(";\n")
                    outp.write("insert into `tmp_surname_rank` values")
                outp.write("({},{},{})".format(id, surname_rank_dict[surname], name_rank_dict[name]))
                if index + 1 < len(all_ids):
                    outp.write(",")
                index += 1
            outp.write(";\n")
            outp.write(
                """
                update declarations_section s 
                join tmp_surname_rank r on s.id=r.id
                set s.surname_rank=r.surname_rank,
                    s.name_rank=r.name_rank;
                """)

    def run_script(self, temp_path):
        cmd = "mysql -u {} -p{} -D {} <  {}".format(
            settings.DATABASES['default']['USER'],
            settings.DATABASES['default']['PASSWORD'],
            settings.DATABASES['default']['NAME'],
            temp_path
        )

        self.logger.info(cmd)
        if os.system(cmd) != 0:
            self.logger.error("running mysql failed!")
            sys.exit(1)

    def handle(self, *args, **options):
        surname_rank_dict, name_rank_dict, all_ids = self.build_dicts()
        temp_path = "tmp.sql"
        self.write_temp_file(all_ids, surname_rank_dict, name_rank_dict, temp_path)
        self.run_script(temp_path)
        os.unlink(temp_path)
        self.logger.info("all done")



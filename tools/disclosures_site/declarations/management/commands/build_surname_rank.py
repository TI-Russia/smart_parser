from common.russian_fio import TRussianFio
from declarations.sql_helpers import run_sql_script
import declarations.models as models
from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand
import os
from collections import defaultdict


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(log_file_name="surname_rank.log")

    def get_surname_and_names(self, person_name):
        fio = TRussianFio(person_name)
        if not fio.is_resolved:
            return None, None
        surname = fio.family_name
        name = "{} {}".format(fio.first_name, fio.patronymic)
        return surname, name

    def build_dicts(self):
        surname_to_name = defaultdict(set)
        name_to_surname = defaultdict(set)
        self.logger.info("read sections")
        cnt = 0
        all_ids = list()
        for s in models.Section.objects.raw("select id, person_name from declarations_section"):
            surname, names = self.get_surname_and_names(s.person_name)
            if surname is not None:
                all_ids.append((s.id, surname, names))
                surname_to_name[surname].add(names)
                name_to_surname[names].add(surname)
                cnt += 1
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
        def get_value_str(seq):
            for id, surname, name in seq:
                yield "({},{},{})".format(id, surname_rank_dict[surname], name_rank_dict[name])

        self.logger.info("create temp file {}".format(temp_path))
        with open(temp_path, "w") as outp:
            outp.write("""
                create temporary table tmp_surname_rank 
                (
                      `id` int,
                      `surname_rank` int,
                      `name_rank` int
                );
                """)
            max_items_in_line = 10000
            for i in range(0, len(all_ids), max_items_in_line):
                outp.write("insert into tmp_surname_rank values ")
                outp.write(",".join(get_value_str(all_ids[i:i+max_items_in_line])))
                outp.write(";\n")

            outp.write(
                """
                update declarations_section s 
                join tmp_surname_rank r on s.id=r.id
                set s.surname_rank=r.surname_rank,
                    s.name_rank=r.name_rank;
                """)

    def handle(self, *args, **options):
        surname_rank_dict, name_rank_dict, all_ids = self.build_dicts()
        temp_path = "tmp.sql"
        self.write_temp_file(all_ids, surname_rank_dict, name_rank_dict, temp_path)
        run_sql_script(self.logger, temp_path)
        os.unlink(temp_path)
        self.logger.info("all done")



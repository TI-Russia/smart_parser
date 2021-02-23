import declarations.models as models
from declarations.russian_fio import TRussianFio

from django.core.management import BaseCommand
import logging
import os
from collections import defaultdict
from django.db import connection


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
        self.regions = dict()
        for r in models.Region.objects.all():
            self.regions[r.id] = r.name


    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            dest='limit',
            type=int,
            default=100000000
        )

    def get_surname_and_names(self, person_name):
        fio = TRussianFio(person_name)
        if not fio.is_resolved:
            return None, None
        return fio.family_name, fio.first_name

    def build_surname_and_name_dicts(self, max_count):
        query = """
            select p.id, p.person_name, o.region_id 
            from declarations_person p
            join declarations_section s on s.person_id=p.id
            join declarations_source_document d on d.id=s.source_document_id 
            join declarations_office o on d.office_id=o.id
            where o.region_id is not null
            limit {}  
        """.format(max_count)
        surnames = defaultdict(int)
        names = defaultdict(int)
        people = set()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id, person_name, region_id in cursor:
                if person_id in people:
                    continue
                people.add(person_id)
                surname, name = self.get_surname_and_names(person_name)
                if surname is not None:
                    surnames[(surname, region_id)] += 1
                    if len(name) > 1:
                        names[(name, region_id)] += 1
        return surnames, names

    def calc_condit_probability(self, dct, filename):
        dct_wo_region = defaultdict(int)
        for (str, region_id), freq in dct.items():
            dct_wo_region[str] += freq
        with open(filename, "w") as outp:
            for (str, region_id), freq in dct.items():
                condit = round(100.0 * float(freq) / dct_wo_region[str], 2)
                region = self.regions[region_id]
                if freq > 1:
                    outp.write("{}\t{}\t{}\t{}\t{}\n".format(str, region, freq, dct_wo_region[str], condit))

    def handle(self, *args, **options):
        surnames, names = self.build_surname_and_name_dicts(options.get('limit', 100000000))
        self.calc_condit_probability(surnames, "surnames.txt")
        self.calc_condit_probability(names, "names.txt")
        self.logger.info("all done")



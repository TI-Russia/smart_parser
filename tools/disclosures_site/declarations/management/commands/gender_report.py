import declarations.models as models
from declarations.russian_fio import TRussianFio
from declarations.rubrics import get_all_rubric_ids, get_russian_rubric_str
from declarations.gender_recognize import TGender, TGenderRecognizer

from django.core.management import BaseCommand
import logging
import os
from collections import defaultdict
from django.db import connection


def setup_logging(logfilename="gender_report.log"):
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
        self.names_masc = set()
        self.names_fem = set()
        self.surnames_masc = set()
        self.surnames_fem = set()
        self.gender_recognizer = TGenderRecognizer()

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

    def build_genders_report(self, max_count, filename):
        query = """
            select p.id, p.person_name, o.region_id, s.rubric_id 
            from declarations_person p
            join declarations_section s on s.person_id=p.id
            join declarations_source_document d on d.id=s.source_document_id 
            join declarations_office o on d.office_id=o.id
            limit {}  
        """.format(max_count)
        rubric_genders = defaultdict(int)
        genders_in_db = defaultdict(int)
        people = set()
        section_count = 0
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id, person_name, region_id, rubric_id in cursor:
                if person_id in people:
                    continue
                people.add(person_id)
                fio = TRussianFio(person_name)
                if not fio.is_resolved:
                    continue
                gender = self.gender_recognizer.recognize_gender(fio)
                if gender is None:
                    continue
                section_count += 1
                genders_in_db[gender] += 1
                rubric_genders[(gender, rubric_id)] += 1

        with open (filename, "w") as outp:
            outp.write("Genders in DB: ")
            outp.write("Gender\tPerson Count\n")
            for k, v in genders_in_db.items():
                outp.write("{}\t{}\n".format(TGender.gender_to_str(k), v))

            outp.write("\nGenders in DB Rubrics: ")
            outp.write("\nRubric\tGender\tPersons in the Rubric\tGender Share\n")
            for rubric in get_all_rubric_ids():
                all_cnt = sum(rubric_genders[(gender, rubric)] for gender in TGender.gender_list())
                if all_cnt > 0:
                    for gender in TGender.gender_list():
                        outp.write("{}\t{}\t{}\t{}\n".format(
                                get_russian_rubric_str(rubric),
                                TGender.gender_to_str(gender),
                                all_cnt,
                                round(100.0 * rubric_genders[(gender, rubric)] / all_cnt, 2),
                                ))

    def handle(self, *args, **options):
        self.logger.info("build_masc_and_fem_names")
        self.gender_recognizer.build_masc_and_fem_names(options.get('limit', 100000000), "names.masc_and_fem.txt")

        self.logger.info("build_masc_and_fem_surnames")
        self.gender_recognizer.build_masc_and_fem_surnames(options.get('limit', 100000000), "surnames.masc_and_fem.txt")

        #self.logger.info("build_person_gender_by_years_report")
        #self.gender_recognizer.build_person_gender_by_years_report(options.get('limit', 100000000), "person.gender_by_years.txt")

        self.logger.info("gender_report")
        self.build_genders_report(100000000, "gender_report.txt")



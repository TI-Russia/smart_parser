import declarations.models as models
from declarations.russian_fio import TRussianFio
from declarations.rubrics import get_all_rubric_ids, get_russian_rubric_str
from declarations.gender_recognize import TGender, TGenderRecognizer

from django.core.management import BaseCommand
import logging
import os
from collections import defaultdict
from django.db import connection
from statistics import median
import gc
import re

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


def fetch_cursor(sql_query):
    with connection.cursor() as cursor:
        cursor.execute(sql_query)
        while True:
            results = cursor.fetchmany(10000)
            if not results:
                break
            for x in results:
                yield x
            gc.collect()


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

    def build_genders_rubrics(self, max_count, filename):
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

    def filter_incomes(self, query):
        unique_name_and_income = set()
        for items in fetch_cursor(query):
            person_name = items[0] if items[0] is not None else items[1]
            income_size = items[2]
            income_year = items[3]
            key = (person_name, income_year, income_size)
            if key in unique_name_and_income:
                continue
            unique_name_and_income.add(key)
            fio = TRussianFio(person_name)
            if not fio.is_resolved:
                continue
            gender = self.gender_recognizer.recognize_gender(fio)
            if gender is None:
                continue
            yield [gender] + list(items[2:])

    def report_income_by_genders(self, incomes_by_genders, outp):
        outp.write("Пол\tЧисло учтенных деклараций\tМедианный доход\tГендерный перекос\n")
        for k, v in incomes_by_genders.items():
            outp.write("{}\t{}\t{}\t{}\n".format(
                TGender.gender_to_Russian_str(k),
                len(v),
                median(v),
                int(100.0 * (median(incomes_by_genders[TGender.masculine]) - median(v)) / median(v))
                )
            )

    def report_income_by_genders_group(self, incomes_by_genders_group, groups, group_name, group_id_to_str_func, outp):
        outp.write("\n\nРубрика\tПол\t{}\tМедианный доход\tГендерный перекос\n".format(group_name))
        for group_id in groups:
            all_cnt = sum(len(incomes_by_genders_group[(gender, group_id)]) for gender in TGender.gender_list())
            if all_cnt > 0:
                for gender in TGender.gender_list():
                    med = median(incomes_by_genders_group[(gender, group_id)])
                    outp.write("{}\t{}\t{}\t{}\t{}\n".format(
                        group_id_to_str_func(group_id),
                        TGender.gender_to_Russian_str(gender),
                        all_cnt,
                        int(med),
                        int(100.0 * (median(incomes_by_genders_group[(TGender.masculine, group_id)]) - med) / med)
                    ))

    def build_genders_incomes(self, max_count, filename, start_year=2010, last_year=2019):
        query = """
            select p.person_name, s.person_name, i.size, s.income_year, s.rubric_id  
            from declarations_section s
            join declarations_income i on i.section_id=s.id
            left join declarations_person p on s.person_id=p.id
            where i.relative = 'D' and i.size > 10000
            limit {}  
        """.format(max_count)
        rubric_genders = defaultdict(list)
        incomes_by_genders = defaultdict(list)
        year_genders = defaultdict(list)
        for gender, income_size, income_year, rubric_id in self.filter_incomes(query):
            incomes_by_genders[gender].append(income_size)
            rubric_genders[(gender, rubric_id)].append(income_size)
            year_genders[(gender, int(income_year))].append(income_size)

        with open(filename, "w") as outp:
            self.report_income_by_genders(incomes_by_genders, outp)
            self.report_income_by_genders_group(rubric_genders, get_all_rubric_ids(),
                                                "Деклараций в рубрике", get_russian_rubric_str, outp)
            self.report_income_by_genders_group(year_genders, range(start_year, last_year + 1),
                                                "Деклараций за этот год", (lambda x: x), outp)


    def build_income_with_spouse(self, max_count, filename, start_year=2010, last_year=2019):
        query = """
            select p.person_name, s.person_name, i.size, s.income_year, s.rubric_id  
            from declarations_section s
            join declarations_income i on i.section_id=s.id
            left join declarations_person p on s.person_id=p.id
            where i.size > 10000 and i.relative = 'S'
            limit {}  
        """.format(max_count)
        rubric_genders = defaultdict(list)
        year_genders = defaultdict(list)
        incomes_by_genders = defaultdict(list)
        for gender, income_size, income_year, rubric_id in self.filter_incomes(query):
            gender = TGender.opposite_gender(gender)
            incomes_by_genders[gender].append(income_size)
            rubric_genders[(gender, rubric_id)].append(income_size)
            year_genders[(gender, int(income_year))].append(income_size)

        with open(filename, "w") as outp:
            self.report_income_by_genders(incomes_by_genders, outp)
            self.report_income_by_genders_group(rubric_genders, get_all_rubric_ids(),
                                                "Деклараций в рубрике", get_russian_rubric_str, outp)
            self.report_income_by_genders_group(year_genders, range(start_year, last_year + 1),
                                                "Деклараций за этот год", (lambda x: x), outp)

    def build_income_first_word_position(self, max_count, filename, start_year=2010, last_year=2019):
        query = """
            select p.person_name, s.person_name, i.size, s.income_year, s.rubric_id, s.position  
            from declarations_section s
            join declarations_income i on i.section_id=s.id
            left join declarations_person p on s.person_id=p.id
            where i.size > 10000 and i.relative = 'D' and length(position) > 0
            limit {}  
        """.format(max_count)

        rubric_genders = defaultdict(list)
        rubric_first_word = defaultdict(int)
        for gender, income_size, income_year, rubric_id, position_str in self.filter_incomes(query):
            position_words = re.split("[\s,;.]", position_str)
            if len(position_words) == 0:
                continue
            first_position_word = position_words[0].lower()
            gender = TGender.opposite_gender(gender)
            rubric_genders[(rubric_id, first_position_word, gender )].append(income_size)
            rubric_first_word[(rubric_id, first_position_word)] += 1

        with open(filename, "w") as outp:
            outp.write("\n\nРубрика\tПол\t{}\tМедианный доход\tДолжность\tГендерный перекос\n")
            for (rubric_id, first_position_word), all_cnt in rubric_first_word.items():
                if all_cnt > 10:
                    masc_incomes = rubric_genders[(rubric_id, first_position_word, TGender.masculine)]
                    if len(masc_incomes) == 0:
                        continue
                    masc_med = median(masc_incomes)
                    for gender in TGender.gender_list():
                        incomes = rubric_genders[(rubric_id, first_position_word, gender)]
                        if len(incomes) == 0:
                            continue
                        med = median(incomes)
                        outp.write("{}\t{}\t{}\t{}\t{}\t{}\n".format(
                            get_russian_rubric_str(rubric_id),
                            first_position_word,
                            TGender.gender_to_Russian_str(gender),
                            all_cnt,
                            int(med),
                            int(100.0 * (masc_med - med) / med)
                        ))

    def build_vehicles(self, max_count, filename):
        with connection.cursor() as cursor:
            cursor.execute('select section_id from declarations_vehicle where relative="D"')
            section_with_vehicles = set(section_id for section_id, in cursor)

        query = """
            select p.person_name, s.person_name, d.office_id, s.income_year, s.rubric_id, s.id  
            from declarations_section s
            left join declarations_person p on s.person_id=p.id
            join declarations_source_document d on d.id=s.source_document_id
            limit {}  
        """.format(max_count)

        rubric_vehicle_positive = defaultdict(int)
        rubric_vehicle_negative = defaultdict(int)
        rubric_vehicle_all = defaultdict(int)
        for gender, office_id, income_year, rubric_id, section_id in self.filter_incomes(query):
            key = (gender, rubric_id)
            if section_id in section_with_vehicles:
                rubric_vehicle_positive[key] += 1
            else:
                rubric_vehicle_negative[key] += 1
            rubric_vehicle_all[rubric_id] += 1

        with open(filename, "w") as outp:
            outp.write("\n\nРубрика\tПол\tКол-во автомобилей в рубрике\tАвтомобилизация\tГендерный перекос\n")
            for rubric_id in get_all_rubric_ids():
                if rubric_vehicle_all[rubric_id] > 0:
                    k = (TGender.masculine, rubric_id)
                    vehicle_index_masc = 100.0 * rubric_vehicle_positive[k] / float (
                            rubric_vehicle_positive[k] + rubric_vehicle_negative[k] + 0.0000001)

                    for gender in TGender.gender_list():
                        k = (gender, rubric_id)
                        vehicle_index = 100.0 * rubric_vehicle_positive[k] / float( rubric_vehicle_positive[k] + rubric_vehicle_negative[k] + 0.0000001)
                        outp.write("{}\t{}\t{}\t{}\t{}\n".format(
                            get_russian_rubric_str(rubric_id),
                            TGender.gender_to_Russian_str(gender),
                            rubric_vehicle_all[rubric_id],
                            int(vehicle_index),
                            int(100.0 * (vehicle_index_masc - vehicle_index) / (vehicle_index + 0.0000001))
                        ))

    def get_sections_with_relative_type(self, relative_code):
        sql = """
            (select section_id from declarations_vehicle where relative="{}") 
            union
            (select section_id from declarations_income where relative="{}")
            union
            (select section_id from declarations_realestate where relative="{}")
        """.format(relative_code, relative_code, relative_code)
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return set(section_id for section_id, in cursor)

    def build_incomplete_family(self, max_count, filename, start_year=2010, last_year=2019):

        section_with_children = self.get_sections_with_relative_type(models.Relative.child_code)
        self.logger.info("section with children: {}".format(len(section_with_children)))

        section_with_spouse = self.get_sections_with_relative_type(models.Relative.spouse_code)
        self.logger.info("section with spouse: {}".format(len(section_with_spouse)))

        query = """
            select p.person_name, s.person_name, i.size, s.income_year, s.rubric_id, s.id  
            from declarations_section s
            join declarations_income i on i.section_id=s.id
            left join declarations_person p on s.person_id=p.id
            where i.relative = 'D' and i.size > 10000
            limit {}  
        """.format(max_count)
        rubric_genders = defaultdict(list)
        incomes_by_genders = defaultdict(list)
        year_genders = defaultdict(list)
        for gender, income_size, income_year, rubric_id, section_id in self.filter_incomes(query):
            if section_id in section_with_spouse:
                continue
            if section_id not in section_with_children:
                continue
            incomes_by_genders[gender].append(income_size)
            rubric_genders[(gender, rubric_id)].append(income_size)
            year_genders[(gender, int(income_year))].append(income_size)

        with open(filename, "w") as outp:
            self.report_income_by_genders(incomes_by_genders, outp)
            self.report_income_by_genders_group(rubric_genders, get_all_rubric_ids(),
                                                "Деклараций в рубрике", get_russian_rubric_str, outp)
            self.report_income_by_genders_group(year_genders, range(start_year, last_year + 1),
                                                "Деклараций за этот год", (lambda x: x), outp)

    def handle(self, *args, **options):
        self.logger.info("build_masc_and_fem_names")
        self.gender_recognizer.build_masc_and_fem_names(options.get('limit', 100000000), "names.masc_and_fem.txt")

        self.logger.info("build_masc_and_fem_surnames")
        self.gender_recognizer.build_masc_and_fem_surnames(options.get('limit', 100000000), "surnames.masc_and_fem.txt")

        #self.logger.info("build_person_gender_by_years_report")
        #self.gender_recognizer.build_person_gender_by_years_report(options.get('limit', 100000000), "person.gender_by_years.txt")

        #self.logger.info("gender_rubric_report")
        #self.build_genders_rubrics(100000000, "gender_report.txt")

        #self.logger.info("gender_income_report")
        #self.build_genders_incomes(100000000, "gender_income_report.txt")

        #self.logger.info("gender_income_spouse_report")
        #self.build_income_with_spouse(100000000, "gender_income_spouse.txt")

        self.logger.info("gender_income_first_word")
        self.build_income_first_word_position(10000000, "gender_income_first_word.txt")

        self.logger.info("vehicles")
        self.build_vehicles(10000000, "vehicles.txt")

        self.logger.info("incomplete_family")
        self.build_incomplete_family(100000000, "incomplete_family.txt")

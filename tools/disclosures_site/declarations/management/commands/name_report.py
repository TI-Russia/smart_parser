import declarations.models as models
from declarations.russian_fio import TRussianFio, POPULAR_RUSSIAN_NAMES
from declarations.gender_recognize import TGender, TGenderRecognizer
from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand
from collections import defaultdict
from django.db import connection
from statistics import median


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(log_file_name="name_report.log")
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

    def build_surname_and_name_by_regions(self, max_count):
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

    def build_surname_and_name_by_years(self, max_count):
        query = """
            select p.id, p.person_name, min(s.income_year) 
            from declarations_section s
            join declarations_person p on s.person_id=p.id
            where s.person_id is not null and s.income_year > 2009
            group by s.person_id
            
            limit {}  
        """.format(max_count)
        surnames = defaultdict(int)
        names = defaultdict(int)
        people = set()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id, person_name, min_year in cursor:
                if person_id in people:
                    continue
                people.add(person_id)
                surname, name = self.get_surname_and_names(person_name)
                if surname is not None:
                    surnames[(surname, min_year)] += 1
                    if len(name) > 1:
                        names[(name, min_year)] += 1
        return surnames, names

    def calc_region_distribution(self, dct, filename):
        region_size = defaultdict(int)
        for (name, region_id), freq in dct.items():
            region_size[region_id] += freq
        with open(filename, "w") as outp:
            for (name, region_id), freq in dct.items():
                region_ratio = round(100.0 * float(freq) / region_size[region_id], 2)
                region_str = self.regions[region_id]
                if freq > 2:
                    outp.write("{}\t{}\t{}\t{}\t{}\t{}\n".format(
                        name,
                        region_str,
                        ("country-level" if name in POPULAR_RUSSIAN_NAMES else "region-level"),
                        freq,
                        region_size[region_id],
                        region_ratio))

    def calc_year_distribution(self, dct, filename):
        year_size = defaultdict(int)
        for (name, year), freq in dct.items():
            year_size[year] += freq

        with open(filename, "w") as outp:
            for (name, year), freq in dct.items():
                year_ratio = round(100.0 * float(freq) / year_size.get(year, 1), 2)
                if freq > 2:
                    outp.write("{}\t{}\t{}\t{}\t{}\n".format(
                        name,
                        year,
                        freq,
                        year_size[name],
                        year_ratio))

    def calc_popular_russian_names_ratio(self, names_year, filename):
        popular_russian_names_year = defaultdict(int)
        other_names_year = defaultdict(int)
        for (name, year), freq in names_year.items():
            if name in POPULAR_RUSSIAN_NAMES[0:20]:
                popular_russian_names_year[year] += freq
            else:
                other_names_year[year] += freq

        with open(filename, "w") as outp:
            for year in popular_russian_names_year.keys():
                rus = popular_russian_names_year[year]
                other = other_names_year[year]
                ratio = int(100.0 * (rus / (rus + other)))
                outp.write("{}\t{}\t{}\t{}\n".format(
                    year,
                    rus,
                    other,
                    ratio))

    def calc_increasing_popularity_names(self, names_year, filename):
        start_year = 2010
        last_year = 2019
        all_year_freq = defaultdict(int)
        year_size = defaultdict(int)
        for (name, year), freq in names_year.items():
            all_year_freq[name] += freq
            gender = self.gender_recognizer.recognize_gender_by_first_name(name)
            if gender is not None:
                year_size[(year, gender)] += freq

        with open(filename, "w") as outp:
            for name, freq in all_year_freq.items():
                if freq < 100:
                    continue
                gender = self.gender_recognizer.recognize_gender_by_first_name(name)
                if gender is None:
                    continue
                freq_2010 = 100.0 * float(names_year.get((name, start_year), 1)) / float(year_size.get((2010, gender), 1))
                freq_2019 = 100.0 * float(names_year.get((name, last_year), 1)) / float(year_size.get((2019, gender), 1))
                outp.write("{}\t{}\t{}\t{}\t{}\t{}\n".format(
                    name,
                    TGender.gender_to_str(gender),
                    freq,
                    freq_2010,
                    freq_2019,
                    round(100.0*float(freq_2010) / freq_2019, 2)
                ))

    def calc_income_by_name(self, max_count, filename):
        query = """
            select p.person_name, s.person_name, i.size, s.income_year  
            from declarations_section s
            join declarations_income i on i.section_id=s.id
            left join declarations_person p on s.person_id=p.id
            where i.relative = 'D' and i.size > 10000
            limit {}  
        """.format(max_count)
        incomes = defaultdict(list)
        unique_name_and_income = set()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_name1, person_name2, income_size, income_year in cursor:
                person_name = person_name1
                if person_name is None:
                    person_name = person_name2
                key = (person_name, income_year, income_size)
                if key in unique_name_and_income:
                    continue
                unique_name_and_income.add(key)
                fio = TRussianFio(person_name)
                if not fio.is_resolved or len(fio.first_name) <= 1:
                    continue
                incomes[fio.first_name].append(income_size)

        with open(filename, "w") as outp:
            for name in incomes.keys():
                if len(incomes[name]) > 50:
                    outp.write("{}\t{}\t{}\n".format(
                        name,
                        len(incomes[name]),
                        median(incomes[name])
                    ))

    def handle(self, *args, **options):
        self.gender_recognizer.build_masc_and_fem_names(report_filename="names.masc_and_fem.txt")
        self.gender_recognizer.build_masc_and_fem_surnames(report_filename="surnames.masc_and_fem.txt")


        surnames_region, names_region = self.build_surname_and_name_by_regions(options.get('limit', 100000000))
        #self.calc_region_distribution(surnames_region, "surnames.region.txt")
        self.calc_region_distribution(names_region, "names.region.txt")

        surnames_year, names_year = self.build_surname_and_name_by_years(options.get('limit', 1000000000))
        #self.calc_year_distribution(surnames_year, "surnames.years.txt")
        self.calc_year_distribution(names_year, "names.years.txt")
        self.calc_popular_russian_names_ratio(names_year, "names.popularity_years.txt")
        self.calc_increasing_popularity_names(names_year, "names.2010_2019_increase.txt")

        self.calc_income_by_name(options.get('limit', 1000000000), "name.income.txt")
        self.logger.info("all done")



import declarations.models as models
from office_db.russia import RUSSIA
from office_db.declarant_group_stat_data import TGroupStatData, TGroupYearSnapshot, TGroupStatDataList
from common.logging_wrapper import setup_logging
from office_db.year_income import TYearIncome

from django.core.management import BaseCommand
from itertools import groupby
from operator import itemgetter
from statistics import median, mean
from django.db import connection
from collections import defaultdict
from datetime import datetime
import os.path


class TGroupIncomeStats:
    def __init__(self):
        self.incomes_by_person = defaultdict(list)

    def add_income(self, person_id: int, year: int, income: int):
        assert person_id is not None
        self.incomes_by_person[person_id].append(TYearIncome(year, income))

    def get_year_incomes(self, year):
        res = list()
        for person_id, incomes in self.incomes_by_person.items():
            for i in incomes:
                if i.year == year:
                    res.append(i.income)
        return res

    def build_v2(self):
        ratios = list()
        for person_id, incomes in self.incomes_by_person.items():
            incomes.sort()
            for i in range(len(incomes) - 1):
                i1 = incomes[i]
                i2 = incomes[i + 1]
                if i1.year + 1 == i2.year:
                    cmp_result = RUSSIA.get_average_nominal_incomes([i1, i2])
                    if cmp_result is None:
                        continue
                    ratios.append(cmp_result.compare_to_all_people_income())
        if len(ratios) == 0:
            return None, None
        else:
            return round(median(ratios), 2), len(ratios)


class TAllGroupIncomeStats:
    def __init__(self):
        self.groups = dict()

    def get_all_group_ids(self):
        return self.groups.keys()

    def add_income(self, group_id: int, person_id: int, year: int, income: int):
        g = self.groups.get(group_id)
        if g is None:
            g = TGroupIncomeStats()
            self.groups[group_id] = g
        g.add_income(person_id, year, income)


def average_income_ratios(person_incomes):
    if len(person_incomes) == 0:
        return -1
    else:
        try:
            avr = median(p.compare_to_all_people_income() for p in person_incomes)
            return round(avr, 2)
        except ZeroDivisionError as exp:
            raise


class BuildOfficeCalculatedParams(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None
        self.income_stat_start_year = None
        self.last_year = None
        self.max_income = 6500000  # see example https://disclosures.ru/person/1408920/

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-year',
            dest='min_year',
            type=int,
            default=2011
        )
        parser.add_argument(
            '--max-year',
            dest='max_year',
            type=int,
            default=None
        )
        parser.add_argument(
            '--directory',
            dest='directory',
        )

    def build_section_incomes(self):
        query = """
            select o.id, s.income_year, i.size, s.person_id 
            from declarations_section s 
            join declarations_office o on s.office_id=o.id  
            join declarations_income i on i.section_id=s.id
            join declarations_source_document d on s.source_document_id=d.id  
            where s.income_year >= {} and
                 s.income_year <= {} and  
                 i.size < {} and

                 i.size > 50000 and
                 s.person_id is not null and
                 d.median_income > 10000 and 
                 i.relative='{}'
            order by o.id
        """.format(self.income_stat_start_year, self.last_year, self.max_income, models.Relative.main_declarant_code)
        office_stats = TAllGroupIncomeStats()
        rubric_stats = TAllGroupIncomeStats()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for office_id, office_items in groupby(cursor, itemgetter(0)):
                rubric_id = RUSSIA.get_office(office_id).rubric_id
                for _, year, income, person_id in office_items:
                    if income / 12 < RUSSIA.get_mrot(year):
                        continue
                    office_stats.add_income(office_id, person_id, year, income)
                    rubric_stats.add_income(rubric_id, person_id, year, income)
        return office_stats, rubric_stats

    def build_aux_office_params(self, office_data: TGroupStatDataList):
        # ignore self.income_stat_start_year
        query = """
            select o.id, min(s.income_year), count(s.id) 
            from declarations_office o
            join declarations_section s on s.office_id = o.id
            where s.income_year >= 2009 and s.income_year <= {}
            group by o.id, s.income_year
        """.format(self.last_year)
        with connection.cursor() as cursor:
            self.logger.info("execute {}".format(query.replace("\n", " ")))
            cursor.execute(query)
            params = defaultdict(dict)
            self.logger.info("read data")
            for office_id, income_year, section_count in cursor:
                ys = office_data.get_or_create_group_data(office_id).get_or_create_year_snapshot(income_year)
                ys.declarants_count = section_count

        query = """
                    select o.id, count(distinct d.id) 
                    from declarations_office o
                    join declarations_section s on s.office_id = o.id
                    join declarations_source_document d on d.id = s.source_document_id
                    group by o.id
                """
        with connection.cursor() as cursor:
            self.logger.info("execute {}".format(query.replace("\n", " ")))
            cursor.execute(query)
            for office_id, cnt in cursor:
                oi = office_data.get_or_create_group_data(office_id)
                oi.source_document_count = cnt

        offices = RUSSIA.offices_in_memory
        child_offices = offices.get_child_offices_dict()
        for office in RUSSIA.iterate_offices():
            office_id = office.office_id
            oi = office_data.get_or_create_group_data(office_id)
            if office.parent_id is None:
                oi.child_office_examples = list()
            else:
                oi.child_office_examples = list(c.office_id for c in child_offices[office_id][:5])
            oi.child_offices_count = len(child_offices[office_id])
            oi.section_count = sum(s.declarants_count for s in oi.year_snapshots.values())
            oi.urls = list(x.url for x in office.office_web_sites if x.can_communicate())

    def build_snapshots(self, input_stats: TAllGroupIncomeStats, output_stats: TGroupStatDataList):
        input_group: TGroupIncomeStats
        for group_id, input_group in input_stats.groups.items():
            output_group = TGroupStatData()

            for year in range(self.income_stat_start_year, self.last_year + 1):
                incomes = input_group.get_year_incomes(year)
                cnt = len(incomes)
                if cnt == 0:
                    continue
                me = median(incomes)
                self.logger.debug("group_id={} year={} median={}, count={}".format(
                    group_id, year, me, cnt
                ))
                s = TGroupYearSnapshot(me, cnt)
                output_group.add_snapshot(year, s)

            if not output_group.is_empty():
                output_group.v2, output_group.v2_size = input_group.build_v2()
                output_stats.add_group(group_id, output_group)

    def init_options(self, options):
        self.options = options
        self.logger = setup_logging("office_report")
        self.last_year = options.get('max_year')
        if self.last_year is None:
            #  on April 1 each year the declarants must send their declarations,
            # wait 1 month.  Let us say the 1st of May is the start of new declaration year
            if datetime.now().month >= 5:
                self.last_year = datetime.now().year - 1
            else:
                self.last_year = datetime.now().year - 2
        self.income_stat_start_year = options.get('min_year')
        if self.income_stat_start_year is None:
            self.income_stat_start_year = self.last_year - 4

        assert self.income_stat_start_year <= self.last_year
        self.directory = options.get('directory')
        if self.directory is None:
            self.directory = os.path.join(os.path.dirname(__file__), "../../../../office_db/data/office_current")

    def handle(self, *args, **options):
        self.init_options(options)

        self.logger.info(
            "build_section_incomes start_year={}, last_year={}".format(self.income_stat_start_year, self.last_year))
        office_stats, rubric_stats = self.build_section_incomes()

        self.logger.info("write to disk offices (directory={})".format(options['directory']))
        office_data = TGroupStatDataList(directory=self.directory, group_type=TGroupStatDataList.office_group,
                                         start_year=self.income_stat_start_year,
                                         last_year=self.last_year)
        self.build_snapshots(office_stats, office_data)
        self.build_aux_office_params(office_data)
        office_data.save_to_disk()
        office_data.write_csv_file(RUSSIA)

        self.logger.info("write to disk rubrics")
        rubric_data = TGroupStatDataList(directory=self.directory,
                                         group_type=TGroupStatDataList.rubric_group,
                                         start_year=self.income_stat_start_year,
                                         last_year=self.last_year)
        self.build_snapshots(rubric_stats, rubric_data)
        rubric_data.save_to_disk()
        rubric_data.write_csv_file(RUSSIA)

        self.logger.info("all done")


Command = BuildOfficeCalculatedParams
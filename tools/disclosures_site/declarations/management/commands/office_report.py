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


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None
        self.start_year = None
        self.last_year = None
        self.max_income = 6500000 # see example https://disclosures.ru/person/1408920/

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
            default=2019
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
        """.format(self.start_year, self.last_year, self.max_income, models.Relative.main_declarant_code)
        office_stats = TAllGroupIncomeStats()
        rubric_stats = TAllGroupIncomeStats()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for office_id, office_items in groupby(cursor, itemgetter(0)):
                rubric_id = RUSSIA.get_office(office_id).rubric_id
                for _, year, income, person_id in office_items:
                    if income/12 < RUSSIA.get_mrot(year):
                        continue
                    office_stats.add_income(office_id, person_id, year, income)
                    rubric_stats.add_income(rubric_id, person_id, year, income)
        return office_stats, rubric_stats

    def build_snapshots(self, input_stats: TAllGroupIncomeStats, output_stats: TGroupStatDataList):
        input_group: TGroupIncomeStats
        for group_id, input_group in input_stats.groups.items():
            output_group = TGroupStatData()

            for year in range(self.start_year, self.last_year + 1):
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

    def handle(self, *args, **options):
        self.options = options
        self.logger = setup_logging("office_report")
        self.start_year = options['min_year']
        self.last_year = options['max_year']

        # rubric_data = TGroupStatDataList(start_year=self.start_year, last_year=self.last_year, group_type=TGroupStatDataList.rubric_group)
        # rubric_data.load_from_disk()
        # rubric_data.write_csv_file(RUSSIA)
        # return

        self.logger.info("build_section_incomes start_year={}, last_year={}".format(self.start_year, self.last_year))
        office_stats, rubric_stats = self.build_section_incomes()

        #self.logger.info("build_person_income_growth start_year={}, last_year={}".format(self.start_year, self.last_year))
        #person_office_incomes, person_rubric_incomes = self.build_person_incomes()

        self.logger.info("write to disk offices")
        office_data = TGroupStatDataList(group_type=TGroupStatDataList.office_group,
                                         start_year=self.start_year, last_year=self.last_year)
        self.build_snapshots(office_stats, office_data)
        office_data.save_to_disk()
        office_data.write_csv_file(RUSSIA)

        self.logger.info("write to disk rubrics")
        rubric_data = TGroupStatDataList(group_type=TGroupStatDataList.rubric_group,
                                         start_year=self.start_year, last_year=self.last_year)
        self.build_snapshots(rubric_stats, rubric_data)
        rubric_data.save_to_disk()
        rubric_data.write_csv_file(RUSSIA)

        self.logger.info("all done")

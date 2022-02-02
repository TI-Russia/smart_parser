import declarations.models as models
from office_db.russian_regions import TRussianRegions
from declarations.region_data import TRossStatData
from declarations.all_russia_stat_info import get_mrot
from declarations.region_year_snapshot import TRegionYearStats, TAllRegionYearStats

from django.core.management import BaseCommand
from itertools import groupby
from operator import itemgetter
from django.db import connection
import scipy.stats
import json


class Command(BaseCommand):
    help = 'create rubric for web_site_snapshots'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.regions = TRussianRegions()
        self.options = None

    def add_arguments(self, parser):
        parser.add_argument(
                '--year',
            dest='year',
            type=int,
        )
        parser.add_argument(
                '--main-report-html',
            dest='main_report_html_path',
            default='/reports/regions2020/index.html'
        )
        parser.add_argument(
            '--output-json',
            dest='output_json'
        )

    def build_declarant_incomes(self, year, max_income=5000000) -> TAllRegionYearStats:
        region_data = TAllRegionYearStats(year, file_name=self.options.get('output_json'))
        minOboronyId = 450
        query = """
            select o.region_id, i.size
            from declarations_section   s 
            join declarations_office o on s.office_id=o.id  
            join declarations_income i on i.section_id=s.id  
            where s.income_year = {} and  
                 i.size < {} and 
                 i.size > 0 and 
                 i.relative='{}' and
                 o.id != {} and
                 o.region_id is  not null and
                 o.region_id != {}
            order by o.region_id, i.size
        """.format(year, max_income, models.Relative.main_declarant_code, minOboronyId, TRussianRegions.Russia_as_s_whole_region_id)
        regions = TRussianRegions()
        mrot = get_mrot(year)
        assert mrot is not None
        with connection.cursor() as cursor:
            cursor.execute(query)
            for region_id, items in groupby(cursor, itemgetter(0)):
                incomes = list(income for _, income in items if income/12 > mrot)
                if region_id == TRussianRegions.Baikonur:
                    continue
                region = regions.get_region_by_id(region_id)
                if region.joined_to is not None:
                    region = regions.get_region_by_id(region.joined_to)
                stat_info = region_data.ross_stat.get_data(region.id, year)
                if stat_info is None:
                    raise Exception(
                        "cannot find stat_info for region.id={}, region.name={}".format(region.id, region.name))
                population = stat_info.population
                population_median_income = region_data.ross_stat.get_or_predict_median_salary(region.id, year)
                if population_median_income is None:
                    raise Exception(
                        "cannot estimate population median_income for region.id={}, region.name={}".format(region.id, region.name))
                s = TRegionYearStats(region.id, region.name, incomes, population_median_income, population,
                                     region_data.ross_stat.get_data(region.id, 2021).er_election_2021)
                region_data.add_snapshot(s)

        region_data.calc_aux_params()
        return region_data

    def print_spearman_corr(self, region_stats):
        x = list()
        y = list()
        for s in region_stats.values():
            if s.region_id is not None and s.citizen_month_median_salary is not None:
                x.append(s.citizen_month_median_salary)
                y.append(s.declarant_month_median_income)

        alpha = 1e-3
        _, p1 = scipy.stats.normaltest(x)
        _, p2 = scipy.stats.normaltest(x)
        if p1 < alpha or p2 < alpha:
            # usually pvalue of normaltests are very low  (<10^-3)  it means it is unlikely that the data came from a normal distribution. For example:
            # so we cannot use pearsonr here
            print("Regional median income are not distributed normally, so we cannot  use Pearson correlation coefficients")
        else:
            print("Pearson correlation coefficients {}".format(scipy.stats.pearsonr(x, y)))

        print("Spearman correlation coefficients {}".format(scipy.stats.spearmanr(x, y)))

    def handle(self, *args, **options):
        self.options = options
        year = self.options['year']
        region_data = self.build_declarant_incomes(year)
        region_data.write_to_disk()
        self.print_spearman_corr(region_stats)

        x = list()
        y = list()
        for s in region_stats.values():
            if s.er_election is not None:
                x.append(s.er_election)
                y.append(s.get_inequality())
        print("Spearman get_inequality vs er_election {}".format(scipy.stats.spearmanr(x, y)))
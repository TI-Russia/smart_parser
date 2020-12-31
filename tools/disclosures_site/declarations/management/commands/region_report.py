import declarations.models as models
from declarations.russian_regions import TRussianRegions

from django.core.management import BaseCommand
from itertools import groupby
from operator import itemgetter, attrgetter
from statistics import median
from django.db import connection
import os
import scipy.stats


class TRegionStats:
    def  __init__(self, region_id, region_name, declarant_incomes, citizen_month_median_income, population):
        self.region_id = region_id
        self.region_name = region_name
        self.declarant_month_median_income = int(median(declarant_incomes) / 12)
        self.declarant_count = len(declarant_incomes)
        self.citizen_month_median_income = citizen_month_median_income
        self.population = population

    def to_json(self):
        return {
            'region' : self.region_name,
            'declarant_month_median_income': self.declarant_month_median_income,
            'declarant_count': self.declarant_count,
            'citizen_month_median_income': self.citizen_month_median_income,
            'population': self.population
        }


class Command(BaseCommand):
    help = 'create rubric for offices'

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

    def build_declarant_incomes(self, year, incomes_all_citizen, population, max_income=5000000):
        minOboronyId =  450
        query = """
            select o.region_id, i.size 
            from declarations_section s 
            join declarations_source_document d on d.id=s.source_document_id 
            join declarations_office o on d.office_id=o.id  
            join declarations_income i on i.section_id=s.id  
            where s.income_year = {} and  
                 i.size < {} and 
                 i.size > 0 and 
                 i.relative='{}' and
                 o.id != {}
            order by o.region_id, i.size
        """.format(year, max_income, models.Relative.main_declarant_code, minOboronyId)
        regions = dict( (r.id, r.name) for r in models.Region.objects.all())
        region_stats = list()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for region_id, items in groupby(cursor, itemgetter(0)):
                incomes = list(income for _, income in items )
                region_name = regions.get(region_id, "")
                s = TRegionStats(region_id, region_name, incomes,
                                 incomes_all_citizen.get(region_id), population.get(region_id))
                region_stats.append(s)
        return region_stats

    #rea csv from https://russia.duck.consulting
    def read_russia_duck_consulting_csv(self, basename, year_to_read):
        filepath = os.path.join(os.path.dirname(__file__), "../../../data/", basename)
        incomes_all_citizen = dict()
        with open(filepath, "r") as inp:
            for line in inp:
                year, region_str, income = line.split(',')
                region = self.regions.get_region_by_str(region_str)
                assert region is not None
                year = int(year)
                if year != year_to_read:
                    continue
                income = income.strip('\n')
                if len(income) > 0:
                    incomes_all_citizen[region.id] = int(float(income))
        return incomes_all_citizen

    def print_pearson_corr(self, region_stats):
        x = list()
        y = list()
        for s in region_stats:
            if s.region_id is not None and s.citizen_month_median_income is not None:
                x.append(s.citizen_month_median_income)
                y.append(s.declarant_month_median_income)
        print("normaltest citizen_month_median_income {}".format(scipy.stats.normaltest(sorted(x))))
        print("normaltest declarant_month_median_income {}".format(scipy.stats.normaltest(y)))
        print("Pearson correlation coefficients {}".format(scipy.stats.pearsonr(x, y)))
        print("Spearman correlation coefficients {}".format(scipy.stats.spearmanr(x, y)))


    def print_regions_stats(self, region_stats):
        region_stats.sort(key=attrgetter('declarant_month_median_income'), reverse=True)
        #print(json.dumps(list(l.to_json() for l in region_stats), ensure_ascii=False, indent=4))
        sum_declarant_month_median_income = 0
        sum_citizen_month_median_income = 0
        declarant_count = 0
        for s in region_stats:
            if s.region_id is not None and s.citizen_month_median_income is not None:
                sum_declarant_month_median_income += s.declarant_month_median_income * s.declarant_count
                sum_citizen_month_median_income += s.citizen_month_median_income * s.declarant_count
                declarant_count += s.declarant_count
        print("Income declarant/citizen ratio for {}: {}, declarant_count={}".format(
            year,
            sum_declarant_month_median_income / sum_citizen_month_median_income,
            declarant_count))

    def build_html_by_regions_stats(self, year, region_stats):
        report_folder = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/regionreports")
        if not os.path.exists(report_folder):
            os.mkdir(report_folder)
        data = list()
        for r in region_stats:
            if r.region_id is None or r.citizen_month_median_income is None:
                continue
            data.append((r.region_id,
                r.region_name,
                r.declarant_month_median_income,
                r.citizen_month_median_income,
                round(r.declarant_month_median_income / r.citizen_month_median_income, 2),
                r.declarant_count,
                r.population,
                int(r.population / r.declarant_count)))

        basename = "region-income-report-{}".format(year)
        with open(os.path.join(report_folder, basename + ".csv"), "w") as outp:
            for r in data:
                outp.write(",".join(map(str, r)) + "\n")

        with open(os.path.join(report_folder, basename + ".html"), "w") as outp:
            outp.write("""
<html>
<head>
    <meta charset="UTF-8">
    <title>Средний доход чиновников за {} год по регионам</title>
    <h1>Средний доход чиновников за {} год по регионам</h1>
    <style>
           table {{ 
            border: 1px solid black;
            border-collapse: collapse;
           }}
           th {{ 
              border: 1px solid black;
              color: blue;
           }}
           td {{ 
             border: 1px solid black;
           }}
    </style>
    
</head>
<table id="statstable">
  <tr>
    <th>Id</th>
    <th>Регион</th>
    <th>Медианный доход чиновника в месяц</th>
    <th>Медианная зарплата работающих граждан</th>
    <th>Отношение дохода чиновника к зарплате граждан</th>
    <th>Кол-во учтенных деклараций</th>
    <th>Население</th>
    <th>Население/Кол-во учтенных деклараций</th>
  </tr>
                       """.format(year, year))
            for r in data:
                td_s = ("<td>{}</td>"*len(r)).format(*r)
                outp.write("<tr>{}</tr>\n".format(td_s))
            outp.write("""
</table>
<br/>
<a href={}> Данные в сsv-формате</a>
<script src="sorttable.js"></script>
<script>
    var table = document.getElementById("statstable");
    table.querySelectorAll(`th`).forEach((th, position) => {{
        th.addEventListener(`click`, evt => sortTable(position + 1));
    }});
</script>
</html>""".format(basename + ".csv"))

    def handle(self, *args, **options):
        self.options = options
        year = self.options['year']
        incomes_all_citizen = self.read_russia_duck_consulting_csv("median_income.csv", year)
        population = self.read_russia_duck_consulting_csv("russia_population.csv", year)
        region_stats = self.build_declarant_incomes(year, incomes_all_citizen, population )
        #self.print_regions_stats(region_stats)
        self.build_html_by_regions_stats(year, region_stats)
        self.print_pearson_corr(region_stats)
import declarations.models as models

from django.core.management import BaseCommand
from itertools import groupby
from operator import itemgetter
from statistics import median, fmean
from django.db import connection
import os


class TOfficeStats:
    def  __init__(self,  declarant_incomes):
        self.declarant_month_median_income = int(median(declarant_incomes) / 12)
        self.declarant_count = len(declarant_incomes)


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

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

    def build_office_common_info(self):
        return dict((o.id, o.name)  for o in models.Office.objects.all())

    def build_declarant_incomes(self, year, max_income=5000000):
        query = """
            select o.id, i.size 
            from declarations_section s 
            join declarations_source_document d on d.id=s.source_document_id 
            join declarations_office o on d.office_id=o.id  
            join declarations_income i on i.section_id=s.id  
            where s.income_year = {} and  
                 i.size < {} and 
                 i.size > 0 and 
                 i.relative='{}'
            order by o.id, i.size
        """.format(year, max_income, models.Relative.main_declarant_code)
        office_stats_for_one_year = dict()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for office_id, items in groupby(cursor, itemgetter(0)):
                incomes = list(income for _,  income in items)
                office_stats_for_one_year[office_id] = TOfficeStats(incomes)
        return office_stats_for_one_year

    def build_html_by_office_stats(self, start_year, end_year, year_stats):
        def th_wrapper(s):
            return "<th><div class=\"clickable\">{}↑↓</div></th>\n".format(s)
        office_common_info = self.build_office_common_info()
        report_folder = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/officereports")
        if not os.path.exists(report_folder):
            os.mkdir(report_folder)
        data = list()
        for office_id in office_common_info.keys():
            row = [office_id, office_common_info[office_id]]
            all_declarant_count = 0
            incomes1 = list()
            incomes2 = list()
            for year in range(start_year, end_year):
                r = year_stats[year].get(office_id)
                if r is None:
                    row.append(-1)
                    row.append(-1)
                else:
                    row.append(r.declarant_month_median_income)
                    row.append(r.declarant_count)
                    all_declarant_count += r.declarant_count
                    if year < start_year + (end_year - start_year) / 2:
                        incomes1.append(r.declarant_month_median_income)
                    else:
                        incomes2.append(r.declarant_month_median_income)

            if all_declarant_count > 10:
                if len(incomes1) > 0 and len(incomes2) > 0:
                    av1 = fmean(incomes1)
                    av2 = fmean(incomes2)
                    delta = int(100 * (av2 - av1) / av1)
                    row.append(delta)
                else:
                    row.append(-1)
                data.append(row)

        basename = "office-income-report"
        with open(os.path.join(report_folder, basename + ".csv"), "w") as outp:
            for r in data:
                outp.write(",".join(map(str, r)) + "\n")

        with open(os.path.join(report_folder, basename + ".html"), "w") as outp:
            outp.write("""
<html>
<head>
    <meta charset="UTF-8">
    <title>Средний доход чиновников по ведомствам</title>
    <h1>Средний доход чиновников по ведомствам</h1>
    <link rel="stylesheet" type="text/css" href="/static/style.css" %}">
    <meta name="description" content="Средний доход российских чиновников (государственных и муниципальных служащих) по ведомствам">
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
    <th style="width: 30%">Ведомство</th>
""")
            for year in range(start_year, end_year):
                outp.write(th_wrapper(year))
                outp.write(th_wrapper("#"))
            outp.write(th_wrapper("Рост(%)"))
            outp.write("</tr>\n")
            for r in data:
                r[1] = "<a href=/office/{}>{}</a>".format(r[0], r[1])
                td_s = (" <td>{}</td>\n"*len(r)).format(*r)
                outp.write("<tr>{}</tr>\n".format(td_s))
            outp.write("""
</table>
<br/>
<a href={}> Данные в сsv-формате</a>
<script src="/static/sorttable.js"></script>
<script>
    var table = document.getElementById("statstable");
    table.querySelectorAll(`th`).forEach((th, position) => {{
        th.addEventListener(`click`, evt => sortTable(position + 1));
    }});
</script>
</html>""".format(basename + ".csv"))

    def handle(self, *args, **options):
        self.options = options
        office_stats = dict()
        start_year = options['min_year']
        end_year = options['max_year'] + 1
        for year in range(start_year, end_year):
            office_stats[year] = self.build_declarant_incomes(year)
        self.build_html_by_office_stats(start_year, end_year, office_stats)

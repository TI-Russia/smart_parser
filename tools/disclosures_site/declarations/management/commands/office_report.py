import declarations.models as models

from django.core.management import BaseCommand
from itertools import groupby
from operator import itemgetter
from statistics import median
from django.db import connection
import os


class TOfficeStats:
    def  __init__(self, office_id, office_name, declarant_incomes):
        self.office_id = office_id
        self.office_name = office_name
        self.declarant_month_median_income = int(median(declarant_incomes) / 12)
        self.declarant_count = len(declarant_incomes)

    def to_json(self):
        return {
            'office' : self.office_name,
            'declarant_month_median_income': self.declarant_month_median_income,
            'declarant_count': self.declarant_count,
        }


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

    def add_arguments(self, parser):
        parser.add_argument(
                '--year',
            dest='year',
            type=int,
        )

    def build_declarant_incomes(self, year, max_income=5000000):
        query = """
            select o.id, o.name, i.size 
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
        office_stats = list()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for office_id, items in groupby(cursor, itemgetter(0)):
                office_name = None
                incomes = list()
                for _, curr_office_name, income in items:
                    incomes.append(income)
                    office_name = curr_office_name
                s = TOfficeStats(office_id, office_name, incomes)
                office_stats.append(s)
        return office_stats

    def build_html_by_office_stats(self, year, office_stats):
        report_folder = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/officereports")
        if not os.path.exists(report_folder):
            os.mkdir(report_folder)
        data = list()
        for r in office_stats:
            if r.office_id is None or r.declarant_count < 10:
                continue
            data.append((r.office_id,
                r.office_name,
                r.declarant_month_median_income,
                r.declarant_count,
            ))

        basename = "office-income-report-{}".format(year)
        with open(os.path.join(report_folder, basename + ".csv"), "w") as outp:
            for r in data:
                outp.write(",".join(map(str, r)) + "\n")

        with open(os.path.join(report_folder, basename + ".html"), "w") as outp:
            outp.write("""
<html>
<head>
    <meta charset="UTF-8">
    <title>Средний доход чиновников за {} год по ведомствам</title>
    <h1>Средний доход чиновников за {} год по ведомствам</h1>
    <meta name="description" content="Средний доход российских чиновников (государственных и муниципальных служащих) по ведомствам за {} год">
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
    <th>Ведомство</th>
    <th>Медианный доход чиновника в месяц</th>
    <th>Кол-во учтенных деклараций</th>
  </tr>
                       """.format(year, year, year))
            for r in data:
                r = list(r)
                r[1] = "<a href=/office/{}>{}</a>".format(r[0], r[1])
                td_s = ("<td>{}</td>"*len(r)).format(*r)
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
        year = self.options['year']
        office_stats = self.build_declarant_incomes(year)
        self.build_html_by_office_stats(year, office_stats)

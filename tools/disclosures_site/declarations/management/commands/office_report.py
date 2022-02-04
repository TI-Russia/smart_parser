import declarations.models as models
from office_db.rubrics import get_russian_rubric_str, get_all_rubric_ids
from office_db.russia import YearIncome, TRussia

from django.core.management import BaseCommand
from itertools import groupby
from operator import itemgetter
from statistics import median
from django.db import connection
import os
from bs4 import BeautifulSoup
from collections import defaultdict


class TIncomeStats:
    def  __init__(self,  declarant_incomes):
        self.year_incomes = declarant_incomes

    def extend_incomes(self, incomes):
        self.year_incomes.extend(incomes)

    def get_declarant_count(self):
        return len(self.year_incomes)

    def get_month_median_income(self, top=None):
        if top is None:
            return int(median(self.year_incomes) / 12)
        else:
            self.year_incomes.sort(reverse=True)
            return int(median(self.year_incomes[0:top]) / 12)


def average_person_incomes(person_incomes):
    if len(person_incomes) == 0:
        return -1
    else:
        return round(median((p.declarant_income / p.population_income) for p in person_incomes), 2)


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None
        self.office_2_name = dict((o.id, o.name)  for o in models.Office.objects.all())
        self.office_2_rubric = dict((o.id, o.rubric_id) for o in models.Office.objects.all())
        self.start_year = None
        self.end_year = None

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

    def build_section_incomes(self, start_year, last_year, max_income=5000000):
        query = """
            select o.id, s.income_year, i.size 
            from declarations_section s 
            join declarations_office o on s.office_id=o.id  
            join declarations_income i on i.section_id=s.id  
            where s.income_year >= {} and
                 s.income_year <= {} and  
                 i.size < {} and 
                 i.size > 50000 and
                 d.median_income > 10000 and 
                 i.relative='{}'
            order by o.id, s.income_year, i.size
        """.format(start_year, last_year, max_income, models.Relative.main_declarant_code)
        office_stats = defaultdict(dict)
        rubric_stats = defaultdict(dict)
        with connection.cursor() as cursor:
            cursor.execute(query)
            for office_id, office_items in groupby(cursor, itemgetter(0)):
                for year, year_items in groupby(office_items, itemgetter(1)):
                    incomes = list(income for _, _, income in year_items)
                    office_stats[year][office_id] = TIncomeStats(incomes)
                    rubric_id = self.office_2_rubric.get(office_id)
                    if rubric_id not in rubric_stats[year]:
                        rubric_stats[year][rubric_id] = TIncomeStats(incomes)
                    else:
                        rubric_stats[year][rubric_id].extend_incomes(incomes)
        return office_stats, rubric_stats

    def build_person_incomes(self, max_income=5000000):
        query = """
            select o.id, s.person_id, s.income_year, i.size 
            from declarations_section s 
            join declarations_office o on s.office_id=o.id  
            join declarations_income i on i.section_id=s.id  
            where   
                 i.size < {} and 
                 i.size > 50000 and
                 s.person_id is not null and
                 d.median_income > 10000 and 
                 i.relative='{}'
            order by o.id, s.person_id, s.income_year
        """.format(max_income, models.Relative.main_declarant_code)

        office_stats_for_one_year = defaultdict(list)
        rubric_stats_for_one_year = defaultdict(list)
        with connection.cursor() as cursor:
            cursor.execute(query)
            for office_id, office_items in groupby(cursor, itemgetter(0)):
                for person_id, person_items in groupby(office_items, itemgetter(1)):
                    incomes = list()
                    for _, _, year, income in person_items:
                        incomes.append(YearIncome(year, income))
                    cmp_result = TRussia.get_average_nominal_incomes(incomes)
                    if cmp_result is not None:
                        office_stats_for_one_year[office_id].append(cmp_result)
                        rubric_id = self.office_2_rubric.get(office_id)
                        rubric_stats_for_one_year[rubric_id].append(cmp_result)
        return office_stats_for_one_year, rubric_stats_for_one_year

    def get_incomes_pairs(self, year_stats, output_row):
        incomes = list()
        office_id = output_row[0]
        incomes_counts = list()
        for year in range(self.start_year, self.end_year):
            r = year_stats[year].get(office_id)
            if r is None:
                output_row.append(-1)
                output_row.append(-1)
            else:
                median_income = r.get_month_median_income()
                output_row.append(median_income)
                output_row.append(r.get_declarant_count())
                if r.get_declarant_count() > 5:
                    incomes.append(YearIncome(year, median_income))
                    incomes_counts.append(r.get_declarant_count())
        if sum(incomes_counts) > 10 and len(incomes) > 1:
            cmp_result = TRussia.get_average_nominal_incomes(incomes)
            output_row.append(cmp_result.population_income)
            output_row.append(cmp_result.declarant_income)

            min_year = cmp_result.min_year - 1
            max_year = cmp_result.max_year
            r_min = year_stats[min_year].get(office_id)
            r_max = year_stats[max_year].get(office_id)
            if r_min is None or r_max is None:
                output_row.append(-1)
            else:
                min_count = min(r_min.get_declarant_count(), r_max.get_declarant_count())
                for x in incomes:
                    if x.year == max_year or x.year == min_year:
                        r = year_stats[x.year].get(office_id)
                        x.income = r.get_month_median_income(min_count)
                cmp_result2 = TRussia.get_average_nominal_incomes(incomes)
                output_row.append(cmp_result2.declarant_income)

            return True
        return False

    def build_table_data_single_offices(self, year_stats, person_stats, rubric_id=None):
        data = list()
        for office_id in self.office_2_name.keys():
            if rubric_id is None or self.office_2_rubric[office_id] == rubric_id:
                row = [office_id,
                       "<a href=/office/{}>{}</a>".format(office_id, self.office_2_name[office_id])
                       ]
                if self.get_incomes_pairs(year_stats, row):
                    row.append(average_person_incomes(person_stats[office_id]))
                    data.append(row)
        return data

    def build_table_data_rubrics(self, year_stats, person_stats):
        data = list()
        for rubric_id in get_all_rubric_ids():
            row = [
                    rubric_id,
                    "<a href=/static/officereports/rubric-{}-income-report.html>{}</a>".format(
                       rubric_id, get_russian_rubric_str(rubric_id))
                  ]

            if self.get_incomes_pairs(year_stats, row):
                row.append(average_person_incomes(person_stats[rubric_id]))
                data.append(row)
        return data

    def print_html_header(self, title, description, outp):
        def th_wrapper(s):
            return "<th><div class=\"clickable\">{}↑↓</div></th>\n".format(s)
        outp.write("""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{}</title>
            <h1>{}</h1>
            <h3>см. <a href="/reports/web_site_snapshots/index.html"> описание построенных показателей </a> </h3>
            <link rel="stylesheet" type="text/css" href="/static/style.css">
            <meta name="description" content="Средний доход российских чиновников (государственных и муниципальных служащих) по ведомствам">
        </head>
        <table id="statstable" class="solid_table">
        <tr>
            <th>Id</th>
            <th style="width: 30%">Ведомство</th>
        """.format(title, title, description))

        for year in range(self.start_year, self.end_year):
            outp.write(th_wrapper(year))
            outp.write(th_wrapper("#"))
        outp.write(th_wrapper("PI"))
        outp.write(th_wrapper("D1(%)"))
        outp.write(th_wrapper("D2(%)"))
        outp.write(th_wrapper("V1(%)"))
        outp.write("</tr>\n")

    def print_html_footer(self, cvs_link, outp):
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
        </html>""".format(cvs_link))

    def build_html_by_office_stats(self,  table_data, subtitle, output_base_name):
        def html_to_text(html_data):
            s = BeautifulSoup(str(html_data), "html.parser")
            return s.getText()

        report_folder = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/officereports")
        if not os.path.exists(report_folder):
            os.mkdir(report_folder)
        cvs_file_name = output_base_name + ".csv"
        with open(os.path.join(report_folder, cvs_file_name), "w") as outp:
            for r in table_data:
                outp.write(",".join(map(html_to_text, r)) + "\n")

        with open(os.path.join(report_folder, output_base_name + ".html"), "w") as outp:
            self.print_html_header(
                "Средний доход чиновников по ведомствам" + subtitle,
                "Средний доход российских чиновников (государственных и муниципальных служащих) по ведомствам" + subtitle,
                outp
            )

            for r in table_data:
                r[1] = "<a href=/office/{}>{}</a>".format(r[0], r[1])
                td_s = (" <td>{}</td>\n"*len(r)).format(*r)
                outp.write("<tr>{}</tr>\n".format(td_s))

            self.print_html_footer(cvs_file_name, outp)

    def handle(self, *args, **options):
        self.options = options
        self.start_year = options['min_year']
        self.end_year = options['max_year'] + 1

        office_stats, rubric_stats = self.build_section_incomes(self.start_year, self.end_year)
        person_office_incomes, person_rubric_incomes = self.build_person_incomes()

        single_offices = self.build_table_data_single_offices(office_stats, person_office_incomes, None)
        self.build_html_by_office_stats(single_offices, "", "office-income-report")

        rubric_incomes = self.build_table_data_rubrics(rubric_stats, person_rubric_incomes)
        self.build_html_by_office_stats(rubric_incomes, " (рубрики)", "rubric-income-report")

        for rubric_id in get_all_rubric_ids():
            single_offices = self.build_table_data_single_offices(office_stats, person_office_incomes, rubric_id)
            self.build_html_by_office_stats(single_offices, " ({})".format(get_russian_rubric_str(rubric_id)), "rubric-{}-income-report".format(rubric_id))

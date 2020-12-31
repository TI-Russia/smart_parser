import declarations.models as models
from django.core.management import BaseCommand
import logging
import os
from collections import defaultdict
import shutil
from datetime import datetime
import urllib.parse


def setup_logging(logfilename="static_sections.log"):
    logger = logging.getLogger("static_sections")
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

    return logger


def build_html_table_line(person_name, id, person_id, income, official_position, income_year, print_year=False):
    person_id = "" if person_id is None else person_id
    official_position = "" if official_position is None else official_position
    html = "<tr><td>{}</td><td><a href=/section/{}>{}</a></td><td>{}</td><td>{}</td><td>{}</td>".format(
        id, id, person_name.strip(), official_position.strip(), person_id, income)
    if print_year:
        html += "<td>{}</td>".format(income_year)
    html += "</tr>"
    return html


def write_section_static_file(office, income_years, sections, output_folder):
    file_name = os.path.join(output_folder, "{}-{}.html".format(office.id, "-".join(map(str, income_years))))
    sections.sort()
    with open(file_name, "w") as outp:
        print_year = len(income_years) > 1
        flexia = "ы" if print_year else ""
        title = "{}, {} год{}".format(office.name, ", ".join(map(str, income_years)), flexia)
        outp.write("<html lang=\"ru\"><head><meta charset=\"UTF-8\"><title>{}</title></head>\n".format(title))
        outp.write("<h1><a href=/section/?office_id={}>{}</a></h1>\n".format(
            office.id, title))
        outp.write("<table><tr><th>ID</th><th>ФИО</th><th>Должность</th><th>Декларант</th><th>Доход</th>")
        if print_year:
            outp.write("<th>Год</th>")
        outp.write("</tr>\n")
        for s in sections:
            outp.write(build_html_table_line(*s, print_year=print_year) + "\n")
        outp.write("</table></html")


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = None

    def add_arguments(self, parser):
        output_folder = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sections")
        parser.add_argument(
            '--output-folder',
            dest='output_folder',
            help='default folder is {}'.format(output_folder),
            default=output_folder
        )

    def handle(self, *args, **options):
        self.logger = setup_logging()
        output_folder = options['output_folder']
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder, ignore_errors=True)
        os.mkdir(output_folder)
        current_year = datetime.now().year
        for office in models.Office.objects.all():
            sections_by_years = defaultdict(list)
            for doc in office.source_document_set.all():
                self.logger.debug("office.id={} document_id={}".format(office.id, doc.id))
                for section in doc.section_set.all():
                    section_line = (section.person_name, section.id, section.person_id,
                                     section.get_declarant_income_size(), section.position, section.income_year)
                    sections_by_years[section.income_year].append(section_line)
            years = list()
            file_sections = list()
            for year, sections in sorted(sections_by_years.items()):
                if year < 2008 or year >= current_year:
                    continue
                years.append(year)
                file_sections.extend(sections)
                if len(file_sections) > 100:
                    write_section_static_file(office, years, file_sections, output_folder)
                    file_sections = list()
                    years = list()

            if len(file_sections) > 0:
                write_section_static_file(office, years, file_sections, output_folder)

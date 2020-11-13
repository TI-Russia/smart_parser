import declarations.models as models
from django.core.management import BaseCommand
import logging
import os
from collections import defaultdict
import shutil

def setup_logging(logfilename="sitemaps.log"):
    logger = logging.getLogger("sitemaps")
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


def build_html_table_line(person_name, id, person_id, income, official_position):
    person_id = "" if person_id is None else person_id
    official_position = "" if official_position is None else official_position
    html = "<tr><td>{}</td><td><a href=/section/{}>{}</a></td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
        id, id, person_name, official_position, person_id, income)
    return html


def write_static_file(office, income_year, sections, sitemap_folder):
    file_name = os.path.join(sitemap_folder, "{}_{}.html".format(office.id, income_year))
    sections.sort()
    with open(file_name, "w") as outp:
        title = "{}, {} год".format(office.name, income_year)
        outp.write("<html lang=\"ru\"><head><meta charset=\"UTF-8\"><title>{}</title></head>\n".format(
            title))
        outp.write("<h1><a href=/section/?office_id={}&income_year={}>{}</a></h1>\n".format(
            office.id, income_year, title))
        outp.write("<table><tr><th>ID</th><th>ФИО</th><th>Должность</th><th>Декларант</th><th>Доход</th></tr>\n")
        for s in sections:
            outp.write(build_html_table_line(*s) + "\n")
        outp.write("</table></html")
    return file_name


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = None

    def handle(self, *args, **options):
        self.logger = setup_logging()
        sitemap_folder = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap")
        if os.path.exists(sitemap_folder):
            shutil.rmtree(sitemap_folder, ignore_errors=True)
        os.mkdir(sitemap_folder)
        sitemap = list()
        for office in models.Office.objects.all():
            sections_by_years = defaultdict(list)
            for doc in office.source_document_set.all():
                self.logger.debug("office.id={} document_id={}".format(office.id, doc.id))
                for section in doc.section_set.all():
                    section_line = (section.person_name, section.id,
                                    section.person_id, section.get_declarant_income_size(), section.position)
                    sections_by_years[section.income_year].append(section_line)
            for year, sections in sections_by_years.items():
                file_path = write_static_file(office, year, sections, sitemap_folder)
                sitemap.append( os.path.join('https://disclosures.ru/static/sitemap', os.path.basename(file_path)))

        with open (os.path.join(sitemap_folder, "sitemap.txt"), "w") as outp:
            for l in sitemap:
                outp.write(l + "\n")

from django.core.management import BaseCommand
from common.logging_wrapper import setup_logging
import declarations.models as models
from office_db.russia import RUSSIA

import urllib.parse
from django.db import connection
import os
import json
import urllib
import tarfile


def build_rare_people(limit=200000):
    query = """
                select distinct p.id, s.name_rank*s.surname_rank
                from declarations_section s 
                join declarations_person p on p.id=s.person_id 
                join declarations_income i on i.section_id=s.id 
                where s.name_rank*s.surname_rank < 5000000000 and 
                      i.size > 1500000 and 
                      i.relative='{}'
                order by s.name_rank*s.surname_rank desc
                limit {}
            """.format(models.Relative.main_declarant_code, limit)

    with connection.cursor() as cursor:
        cursor.execute(query)
        for person_id, name_and_surname_rank in cursor:
            yield '/person/{}'.format(person_id)


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = None
        self.sitemaps = list()
        self.tar = None
        self.all_written_urls = set()

    def add_arguments(self, parser):
        parser.add_argument(
            '--region-report-folder',
            dest='region_report_folder',
            default=os.path.join(os.path.dirname(__file__), "../../../disclosures/static/regionreports")
        )
        parser.add_argument(
            '--office-report-folder',
            dest='office_report_folder',
            default=os.path.join(os.path.dirname(__file__), "../../../disclosures/static/officereports")
        )
        rare_people_path = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap-rare-people.xml")
        parser.add_argument(
            '--rare-people-file-pattern',
            dest='rare_people_file_pattern',
            help='output sitemap  file, default is {}'.format(rare_people_path),
            default=rare_people_path
        )

        popular_site_pages_sitemap_pattern = os.path.join(os.path.dirname(__file__),
                                                  "../../../disclosures/static/sitemap-popular-site-pages.xml")
        parser.add_argument(
            '--popular-site-pages-pattern',
            dest='popular_site_pages_sitemap_pattern',
            help='output sitemap  file, default is {}'.format(popular_site_pages_sitemap_pattern),
            default=popular_site_pages_sitemap_pattern
        )
        parser.add_argument(
            '--access-log-squeeze',
            dest='access_log_squeeze',
            help='output of command access_log_squeeze.py'
        )

        parser.add_argument(
            '--output-file',
            dest='output_file',
            default=os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap.xml")
        )

        parser.add_argument(
            "--tar-path",
            dest='tar_path'
            )

    def delete_site_map_xml_by_pattern(self, file_pattern):
        folder = os.path.dirname(file_pattern)
        for f in os.listdir(folder):
            if f.startswith(os.path.basename(os.path.splitext(file_pattern)[0])):
                filepath = os.path.join(folder, f)
                self.logger.info("rm {}".format(filepath))
                os.unlink(filepath)

    def add_to_tar(self, path):
        arcname = path[path.find('/disclosures/static/') + 1:]
        self.tar.add(path, arcname=arcname)

    def filter_by_already_written(self, url_paths):
        for u in url_paths:
            if u not in self.all_written_urls:
                yield u

    def write_sitemap(self, url_paths, output_path, priority=0.5):
        self.logger.info("create sitemap {} urls_count: {}".format(output_path, len(url_paths)))
        with open(output_path, "w") as outp:
            outp.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            outp.write("<urlset xmlns=\"https://www.sitemaps.org/schemas/sitemap/0.9\">\n")
            for p in url_paths:
                url = urllib.parse.urljoin("https://disclosures.ru", p)
                outp.write("<url><loc>{}</loc>".format(url))
                if priority != 0.5:
                    outp.write("<priority>{}</priority>".format(priority))
                outp.write("</url>\n")
                self.all_written_urls.add(p)
            outp.write("</urlset>\n")
        self.add_to_tar(output_path)

    # no more than 50000 urls in one sitemap.xml
    def write_sitemaps_by_chunks(self, file_pattern, url_paths, chunk_size=49500):
        self.delete_site_map_xml_by_pattern(file_pattern)
        file_index = 1
        for i in range(0, len(url_paths), chunk_size):
            filepath, extension = os.path.splitext(file_pattern)
            chunk_output_sitemap = "{}-{}{}".format(filepath, file_index, extension)
            self.sitemaps.append(os.path.basename(chunk_output_sitemap))
            self.write_sitemap(url_paths[i:i+chunk_size], chunk_output_sitemap)

            file_index += 1

    def build_rare_people_sitemaps(self, file_pattern):
        self.logger.info("build_rare_people_sitemaps")
        persons = list(build_rare_people())
        self.logger.info("found {} people".format(len(persons)))
        self.write_sitemaps_by_chunks(file_pattern, persons)

    def build_report_sitemap(self, report_folder):
        self.logger.info("build_report_sitemap for {}".format(report_folder))
        subfolder = os.path.basename(report_folder)
        sitemap_path = os.path.join(report_folder, "sitemap.xml")
        url_paths = list("static/{}/{}".format(subfolder, f) for f in os.listdir(report_folder) if f.endswith('.html'))
        self.write_sitemap(url_paths, sitemap_path, priority=0.8)
        self.sitemaps.append('static/{}/sitemap.xml'.format(subfolder))

    def build_popular_site_pages_sitemap(self, input_popular_site_pages_path, sitemap_path):
        popular = list()
        with open(input_popular_site_pages_path) as inp:
            for line in inp:
                request = json.loads(line.strip())
                popular.append("/{}/{}".format(request['record_type'], request['record_id']))

        popular_filtered = list(self.filter_by_already_written(popular))
        self.logger.info("filter requests by already written urls ({} -> {})".format(len(popular),
                                                                                     len(popular_filtered)))
        self.write_sitemaps_by_chunks(sitemap_path, popular_filtered)

    def build_offices_sitemap(self):
        self.logger.info("build_offices_sitemaps")
        sitemap_path = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap-office.xml")
        url_paths = list()
        for o in RUSSIA.iterate_offices():
            doc_cnt = RUSSIA.calc_data_current.office_stats.get_group_data(o.office_id).source_document_count
            if doc_cnt is not None and doc_cnt > 10:
                url_paths.append("office/{}".format(o.office_id))
        self.write_sitemap(url_paths, sitemap_path, priority=0.4)
        self.sitemaps.append(os.path.basename(sitemap_path))

    def build_main_sitemap(self):
        sitemap_path = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap-main.xml")
        url_paths = ["",
                     "about.html",
                     "permalinks.html",
                     "smart_parser_spec.html",
                     "second_office.html",
                     "statistics",
                     "office",
                     "reports/car-brands/car-brands-by-years.html",
                     "reports/car-brands/index.html",
                     "reports/names/index.html",
                     "reports/genders/index.html",
                     "reports/web_site_snapshots/index.html",
                     "reports/regions/index.html",
                     "reports/new-car/index.html",
                     "reports/offices/index.html",
                     "reports/regions2020/index.html",
                     "reports/offices2020/index.html",
                     ""]
        self.write_sitemap(url_paths, sitemap_path, priority=1.0)
        self.sitemaps.append(os.path.basename(sitemap_path))

    def build_sitemap_index(self):
        main_sitemap_index_path = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap.xml")
        with open(main_sitemap_index_path, "w") as outp:
            outp.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            outp.write("<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n")
            for s in self.sitemaps:
                url = urllib.parse.urljoin("https://disclosures.ru", s)
                outp.write("<sitemap><loc>{}</loc></sitemap>\n".format(url))
            outp.write("</sitemapindex>\n")
        self.add_to_tar(main_sitemap_index_path)

    def handle(self, *args, **options):
        self.logger = setup_logging(log_file_name="generate_sitemap.log")
        if os.path.exists(options['tar_path']):
            os.unlink(options['tar_path'])
        self.tar = tarfile.open(options['tar_path'], "x")
        self.build_rare_people_sitemaps(options['rare_people_file_pattern'])
        self.build_report_sitemap(options["region_report_folder"])
        self.build_report_sitemap(options["office_report_folder"])
        self.build_popular_site_pages_sitemap(options['access_log_squeeze'],
                                              options['popular_site_pages_sitemap_pattern'])
        self.build_main_sitemap()
        self.build_sitemap_index()
        self.build_offices_sitemap()
        self.tar.close()
        self.logger.info("all urls count in all sitemaps: {}".format(len(self.all_written_urls)))


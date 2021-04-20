from django.core.management import BaseCommand
from common.logging_wrapper import setup_logging
import declarations.models as models
from common.access_log import get_human_requests

import urllib.parse
from django.db import connection
import os
import re
import urllib
from collections import defaultdict
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
            yield person_id


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = None
        self.tar = None

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
        parser.add_argument(
            '--output-file',
            dest='output_file',
            default=os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap.xml")
        )
        parser.add_argument(
            "--access-log-folder",
            dest='access_log_folder',
            default="/home/sokirko/declarator_hdd/Yandex.Disk/declarator/nginx_logs/")

        parser.add_argument(
            "--tar-path",
            dest='tar_path'
            )

    def delete_rare_people_xml(self, file_pattern):
        folder = os.path.dirname(file_pattern)
        for f in os.listdir(folder):
            if f.startswith( os.path.basename(os.path.splitext(file_pattern)[0])):
                filepath = os.path.join(folder, f)
                self.logger.info("rm {}".format(filepath))
                os.unlink(filepath)

    def add_to_tar(self, path):
        arcname = path[path.find('/disclosures/static/') + 1:]
        self.tar.add(path, arcname=arcname)

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
            outp.write("</urlset>\n")
        self.add_to_tar(output_path)

    def build_rare_people_sitemaps(self, file_pattern):
        persons = list(build_rare_people())
        self.logger.info("found {} people".format(len(persons)))

        # no more than 50000 urls in one sitemap.xml
        file_index = 1
        chunk_size = 49500
        result_sitemaps = list()
        for i in range(0, len(persons), chunk_size):
            filepath, extension = os.path.splitext(file_pattern)
            chunk_output_sitemap = "{}-{}{}".format(filepath, file_index, extension)
            result_sitemaps.append( os.path.basename(chunk_output_sitemap))
            file_index += 1
            url_paths = list('/person/{}'.format(person_id) for person_id in persons[i:i + chunk_size])
            self.write_sitemap(url_paths, chunk_output_sitemap)
        return result_sitemaps

    def build_report_sitemap(self, report_folder):
        subfolder = os.path.basename(report_folder)
        sitemap_path = os.path.join(report_folder, "sitemap.xml")
        url_paths = list("static/{}/{}".format(subfolder, f) for f in os.listdir(report_folder) if f.endswith('.html'))
        self.write_sitemap(url_paths, sitemap_path, priority=0.8)
        return 'static/{}/sitemap.xml'.format(subfolder)

    def build_popular_site_pages_sitemap(self, access_log_folder, sitemap_path):
        requests = defaultdict(int)
        for x in os.listdir(access_log_folder):
            if x.startswith('access'):
                path = os.path.join(access_log_folder, x)
                for r in get_human_requests(path):
                    if re.match('^/(section|person)/[0-9]+/?$', r):
                        r = r.rstrip('/')
                        requests[r] += 1
        if len(requests) > 30000: # filter requests in future by freq
            min_freq = 2
            popular = list(request for request, freq in requests.items() if freq >= min_freq)
        else:
            popular = list(requests.keys())
        self.write_sitemap(popular, sitemap_path)

    def build_main_sitemap(self):
        sitemap_path = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap-main.xml")
        url_paths = ["",
                     "about.html",
                     "permalinks.html",
                     "smart_parser_spec.html",
                     "statistics",
                     "office",
                     "reports/car-brands/car-brands-by-years.html",
                     "reports/car-brands/index.html",
                     "reports/names/index.html",
                     "reports/genders/index.html",
                     "reports/web_site_snapshots/index.html",
                     "reports/regions/index.html",
                     ""]
        self.write_sitemap(url_paths, sitemap_path, priority=1.0)
        return 'sitemap-main.xml'

    def write_sitemap_index_entry(self, sitemap_url_path, outp):
        url = urllib.parse.urljoin("https://disclosures.ru", sitemap_url_path)
        outp.write("<sitemap><loc>{}</loc></sitemap>\n".format(url))

    def handle(self, *args, **options):
        self.logger = setup_logging(log_file_name="generate_sitemap.log")
        if os.path.exists(options['tar_path']):
            os.unlink(options['tar_path'])
        self.tar = tarfile.open(options['tar_path'], "x")
        main_sitemap_index_path = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap.xml")
        popular_site_pages_path = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap-popular-site-pages.xml")

        self.delete_rare_people_xml(options['rare_people_file_pattern'])
        rare_people_sitemaps = self.build_rare_people_sitemaps(options['rare_people_file_pattern'])

        region_sitemap = self.build_report_sitemap(options["region_report_folder"])
        office_sitemap = self.build_report_sitemap(options["office_report_folder"])
        self.build_popular_site_pages_sitemap(options['access_log_folder'], popular_site_pages_path)

        main_sitemap = self.build_main_sitemap()

        with open(main_sitemap_index_path, "w") as outp:
            outp.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            outp.write("<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n")
            self.write_sitemap_index_entry(main_sitemap, outp)
            for s in rare_people_sitemaps:
                self.write_sitemap_index_entry(s, outp)
            self.write_sitemap_index_entry(region_sitemap, outp)
            self.write_sitemap_index_entry(office_sitemap, outp)
            self.write_sitemap_index_entry(os.path.basename(popular_site_pages_path), outp)
            outp.write("</sitemapindex>\n")
        self.add_to_tar(main_sitemap_index_path)
        self.tar.close()
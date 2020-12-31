from django.core.management import BaseCommand
import os
import urllib.parse


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--region-report-folder',
            dest='region_report_folder',
            default=os.path.join(os.path.dirname(__file__), "../../../disclosures/static/regionreports")
        )
        parser.add_argument(
            '--static-section-folder',
            dest='static_section_folder',
            default=os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sections")
        )
        parser.add_argument(
            '--output-file',
            dest='output_file',
            default=os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap.xml")
        )

    def write_url(self, path, outp, priority=0.5):
        url = urllib.parse.urljoin("https://disclosures.ru", path)
        outp.write("<url><loc>{}</loc>".format(url))
        if priority != 0.5:
            outp.write("<priority>{}</priority>".format(priority))
        outp.write("</url>\n")

    def handle(self, *args, **options):
        region_report_folder = options["region_report_folder"]
        static_section_folder = options["static_section_folder"]
        sitemap_path = os.path.join(os.path.dirname(__file__), "../../../disclosures/static/sitemap.xml")
        with open(sitemap_path, "w") as outp:
            outp.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            outp.write("<urlset xmlns=\"https://www.sitemaps.org/schemas/sitemap/0.9\">\n")
            self.write_url("", outp, priority=1.0)
            self.write_url("about.html", outp, priority=1.0)
            self.write_url("statistics", outp, priority=1.0)
            self.write_url("office", outp, priority=0.8)
            for f in os.listdir(region_report_folder):
                if f.endswith('.html'):
                    self.write_url("static/regionreports/{}".format(f), outp, priority=0.8)
            for f in os.listdir(static_section_folder):
                if f.endswith('.html'):
                    self.write_url("static/sections/{}".format(f), outp, priority=0.5)
            outp.write("</urlset>\n")
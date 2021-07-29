from web_site_db.web_sites import TDeclarationWebSiteList
from common.logging_wrapper import setup_logging
import declarations.models as models
from common.urllib_parse_pro import TUrlUtf8Encode

from django.core.management import BaseCommand
from django.db import connection
from collections import defaultdict
import datetime


def get_child_offices(office, max_count=5):
    if office.parent_id is None:
        return ""
    cnt = 0
    for x in models.Office.objects.all().filter(parent_id=office.id):
        yield x.id, x.name
        cnt += 1
        if cnt >= max_count:
            break



class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(log_file_name="build_office_calculated_params.log")

    def handle(self, *args, **options):
        web_sites_db = TDeclarationWebSiteList(self.logger, TDeclarationWebSiteList.default_input_task_list_path).load_from_disk()
        office_to_urls = web_sites_db.build_office_to_main_website()
        query = """
            select o.id, min(s.income_year), count(s.id) 
            from declarations_office o
            join declarations_source_document d on d.office_id = o.id
            join declarations_section s on s.source_document_id = d.id
            where s.income_year >= 2009 and s.income_year < {}
            group by o.id, s.income_year
        """.format(datetime.datetime.now().year)
        with connection.cursor() as cursor:
            self.logger.info("execute {}".format(query.replace("\n", " ")))
            cursor.execute(query)
            params = defaultdict(dict)
            self.logger.info("read data")
            for office_id, income_year, section_count in cursor:
                params[office_id][income_year] = section_count
        self.logger.info("update declarations_office, office count = {}".format(len(params)))
        for o in models.Office.objects.all():
            o.calculated_params = {
                "section_count_by_years":  params[o.id],
                "child_offices_count": models.Office.objects.all().filter(parent_id=o.id).count(),
                "child_office_examples": list(get_child_offices(o)),
                "source_document_count": o.source_document_set.count(),
                "section_count": sum(params[o.id].values()),
                "urls": list(office_to_urls[o.id])
            }
            o.save()



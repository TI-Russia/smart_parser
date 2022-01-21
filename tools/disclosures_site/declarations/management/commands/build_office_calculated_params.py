from common.logging_wrapper import setup_logging
import declarations.models as models
from office_db.offices_in_memory import TOfficeTableInMemory, TOfficeInMemory


from django.core.management import BaseCommand
from django.db import connection
from collections import defaultdict
import datetime
from django.db import transaction


class BuildOfficeCalculatedParams(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(log_file_name="build_office_calculated_params.log")

    def handle(self, *args, **options):
        offices = TOfficeTableInMemory()
        offices.read_from_local_file()
        query = """
            select o.id, min(s.income_year), count(s.id) 
            from declarations_office o
            join declarations_section s on s.office_id = o.id
            where s.income_year >= 2009 and s.income_year < {}
            group by o.id, s.income_year
        """.format(datetime.datetime.now().year)
        with connection.cursor() as cursor:
            self.logger.info("execu te {}".format(query.replace("\n", " ")))
            cursor.execute(query)
            params = defaultdict(dict)
            self.logger.info("read data")
            for office_id, income_year, section_count in cursor:
                params[office_id][income_year] = section_count
        self.logger.info("update declarations_office, office count = {}".format(len(params)))

        query = """
                    select o.id, count(distinct d.id) 
                    from declarations_office o
                    join declarations_section s on s.office_id = o.id
                    join declarations_source_document d on d.id = s.source_document_id
                    group by o.id
                """
        with connection.cursor() as cursor:
            self.logger.info("execute {}".format(query.replace("\n", " ")))
            cursor.execute(query)
            office_to_doc_count = dict(cursor)

        self.logger.info("set calculated_params...")
        child_offices = offices.get_child_offices_dict()
        with transaction.atomic():
            for o in models.Office.objects.all():
                office: TOfficeInMemory
                office = offices.offices[o.id]
                if office.parent_id is None:
                    child_examples = list()
                else:
                    child_examples = list((child.office_id, child.name) for child in child_offices[o.id][:5])
                o.calculated_params = {
                    "section_count_by_years":  params[o.id],
                    "child_offices_count": len(child_offices[o.id]),
                    "child_office_examples": child_examples,
                    "source_document_count": office_to_doc_count.get(o.id, 0),
                    "section_count": sum(params[o.id].values()),
                    "urls": list(x.url for x in office.office_web_sites if x.can_communicate())
                }
                o.save()
        self.logger.info("all done")

Command=BuildOfficeCalculatedParams
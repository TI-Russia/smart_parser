from django.core.management import BaseCommand
import declarations.models as models
from declarations.rubrics import TOfficeRubrics, convert_municipality_to_education
from concurrent.futures import ProcessPoolExecutor

from django.db import transaction
import sys

FIRST_CALL_SET_RUBRIC_IN_SUBPROCESS = True


def set_rubric(document_id):
    document_id = document_id[0]
    global FIRST_CALL_SET_RUBRIC_IN_SUBPROCESS
    if FIRST_CALL_SET_RUBRIC_IN_SUBPROCESS:
        from django.db import connection
        connection.connect()
        FIRST_CALL_SET_RUBRIC_IN_SUBPROCESS = False
    src_doc = models.Source_Document.objects.get(id=document_id)
    with transaction.atomic():
        for section in src_doc.section_set.all():
            section.rubric_id = src_doc.office.rubric_id
            if section.position is not None and section.rubric_id == TOfficeRubrics.Municipality:
                res = convert_municipality_to_education(section.position)
                if res:
                    sys.stdout.write('{} {}\n'.format(res, section.id, section.position))
                    section.rubric_id = TOfficeRubrics.Education
            section.save()


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        pool = ProcessPoolExecutor(max_workers=4)
        documents_ids = models.Source_Document.objects.values_list('id')
        pool.map(set_rubric, documents_ids)


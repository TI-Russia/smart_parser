from django.core.management import BaseCommand
import declarations.models as models
from office_db.rubrics import TOfficeRubrics
from concurrent.futures import ProcessPoolExecutor
from office_db.offices_in_memory import TOfficeTableInMemory

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
            if section.rubric_id is not None and section.rubric_id != src_doc.office.rubric_id:
                sys.stdout.write('set rubric {} to section {}\n'.format(src_doc.office.rubric_id, section.id))

            section.rubric_id = src_doc.office.rubric_id
            if section.position is not None and section.rubric_id == TOfficeRubrics.Municipality:
                res = TOfficeTableInMemory.convert_municipality_to_education(section.position)
                if res:
                    sys.stdout.write('{} {}\n'.format(res, section.id, section.position))
                    section.rubric_id = TOfficeRubrics.Education
            section.save()


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        pool = ProcessPoolExecutor(max_workers=2)
        documents_ids = models.Source_Document.objects.values_list('id')
        pool.map(set_rubric, documents_ids)


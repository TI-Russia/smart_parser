from django.core.management import BaseCommand
import sys
import declarations.models as models
from declarations.rubrics import TOfficeRubrics, convert_municipality_to_education


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        for s in models.Section.objects.filter(source_document__office__rubric_id=TOfficeRubrics.Municipality):
            s.rubric_id = s.source_document.office.rubric_id
            if s.position is not None and s.source_document.office.rubric_id == TOfficeRubrics.Municipality:
                res = convert_municipality_to_education(s.position)
                if res:
                    sys.stdout.write('{} {}\n'.format(res, s.id, s.position))
                    s.rubric_id = TOfficeRubrics.Education


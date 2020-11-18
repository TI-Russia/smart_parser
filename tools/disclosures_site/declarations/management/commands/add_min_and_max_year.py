from django.core.management import BaseCommand
import declarations.models as models
# temporal script

class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        for s in models.Source_Document.objects.all():
            sections = s.section_set.all()
            if len(sections) > 0:
                s.min_income_year = min (s.income_year for s in sections)
                s.max_income_year = max (s.income_year for s in sections)
                s.section_count = len(sections)
                s.save()

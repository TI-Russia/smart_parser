import declarations.models as models
from common.logging_wrapper import setup_logging
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'all ratings'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None


    def handle(self, *args, **options):
        logger = setup_logging("fix_fsin")
        for s in models.Section.objects.filter(rubric_id=10):
            prev_id = 0
            incomes = set()
            for i in s.income_set.all():
                key = (i.size, i.relative_index)
                if prev_id == 0 or i.id < prev_id + 200:
                    incomes.add(key)
                else:
                    logger.debug("delete income id={}".format(i.id)
                    assert key in incomes

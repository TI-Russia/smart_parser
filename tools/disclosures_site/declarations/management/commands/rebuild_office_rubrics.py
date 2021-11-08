from office_db.offices_in_memory import TOfficeTableInMemory
from office_db.rubrics import get_russian_rubric_str
from django.core.management import BaseCommand
from common.logging_wrapper import setup_logging
import declarations.models as models


class Command(BaseCommand):
    help = 'create rubric for web_site_snapshots'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            dest='verbose',
            type=int,
            help='set verbosity, default is DEBUG',
            default=0
        )

    def handle(self, *args, **options):
        logger = setup_logging(log_file_name="build_rubric.log")
        office_hierarchy = TOfficeTableInMemory(use_office_types=False)
        office_hierarchy.read_from_table(models.Office.objects.all())
        for office in models.Office.objects.all():
            rubric_id = office_hierarchy.build_office_rubric(logger, office.id)
            if rubric_id is not None and rubric_id != office.rubric_id:
                logger.debug("set office rubric_id from {} to {} for {}".format(
                    get_russian_rubric_str(office.rubric_id),
                    get_russian_rubric_str(rubric_id), office.name))
                office.rubric_id = rubric_id
                office.save()



from declarations.serializers import normalize_fio_before_db_insert
from django.core.management import BaseCommand
import declarations.models as models
from common.logging_wrapper import setup_logging


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        logger = setup_logging(log_file_name="normalize_fio.log")
        for section in models.Section.objects.all():
            person_name = normalize_fio_before_db_insert(section.person_name)
            if person_name != section.person_name:
                logger.debug("normalize {} -> {}".format(section.person_name, person_name))
                section.person_name = person_name
                section.save()



from declarations.serializers import normalize_fio_before_db_insert
from django.core.management import BaseCommand
import declarations.models as models
import logging
import os

def setup_logging(logfilename="normalize_fio.log"):
    logger = logging.getLogger("build_rubric")
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        logger = setup_logging()
        for section in models.Section.objects.all():
            person_name = normalize_fio_before_db_insert(section.person_name)
            if person_name != section.person_name:
                logger.debug("normalize {} -> {}".format(section.person_name, person_name))
                section.person_name = person_name
                section.save()



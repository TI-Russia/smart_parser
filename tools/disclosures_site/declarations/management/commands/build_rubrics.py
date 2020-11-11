from declarations.rubrics import build_rubrics
from django.core.management import BaseCommand
import logging
import os


def setup_logging(logfilename="build_rubric.log"):
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
    help = 'create rubric for offices'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        build_rubrics(setup_logging())

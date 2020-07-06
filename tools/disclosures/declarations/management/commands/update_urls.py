from declarations.input_json_specification import dhjs
import json
from declarations.models import SPJsonFile
from django.core.management import BaseCommand
import logging
import os


def setup_logging(logfilename="update_urls.log"):
    logger = logging.getLogger("copy_person")
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
    help = 'copy person id from declarator to disclosures'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

    def add_arguments(self, parser):
        parser.add_argument(
                '--dlrobot-human',
            dest='dlrobot_human',
            help='dlrobot_human.json'
        )

    def handle(self, *args, **options):
        logger = setup_logging()
        with open(options['dlrobot_human'], "r") as inp:
            dlrobot_human = json.load(inp)
        files_count = 0
        if dhjs.file_collection in dlrobot_human:
            web_sites = dlrobot_human[dhjs.file_collection]
        else:
            web_sites = dlrobot_human

        for web_site_info in web_sites.values():
            for sha256, file_info in web_site_info.items():
                try:
                    file = SPJsonFile.objects.filter(sha256=sha256).all()[:1].get()
                except Exception as exp:
                    logger.error("cannot find file with sha256={}".format(sha256))
                    continue
                declarator_document_file_url = file_info.get(dhjs.declarator_document_file_url)
                if declarator_document_file_url is not None:
                    file.declarator_document_file_url = declarator_document_file_url

                dlrobot_url = file_info.get(dhjs.dlrobot_url)
                if dlrobot_url is not None:
                    file.dlrobot_url = dlrobot_url
                file.save()
                files_count += 1
        logger.info("updated {} record in db".format(files_count))

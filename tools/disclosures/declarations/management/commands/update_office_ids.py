from declarations.input_json_specification import dhjs
import json
from declarations.models import Source_Document
from django.core.management import BaseCommand
import logging
import os


def setup_logging(logfilename="update_office_ids.log"):
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
            help='dlrobot_human.json human_files.json'
        )

    def handle(self, *args, **options):
        logger = setup_logging()
        with open(options['dlrobot_human'], "r") as inp:
            dlrobot_human = json.load(inp)
            website_to_office = dict()
            for office_id, websites in dlrobot_human[dhjs.offices_to_domains].items():
                for website in websites:
                    assert website not in website_to_office
                    website_to_office[website] = office_id
            files_count = 0
            for file in Source_Document.objects.all():
                if file.declarator_document_file_url is None:
                    new_office_id = website_to_office.get(file.web_domain)
                    if new_office_id is  None:
                        logger.error(
                            "cannot find website {}  in mapping, file.id={} ".format(file.web_domain, file.id))
                    elif int(new_office_id) != file.office_id:
                        logger.debug("update file.id={}, office_id {}->{} ".format(file.id, file.office_id, new_office_id))
                        file.office_id = int(new_office_id)
                        file.save()
                        files_count += 1
        logger.info("updated {} record in db".format(files_count))

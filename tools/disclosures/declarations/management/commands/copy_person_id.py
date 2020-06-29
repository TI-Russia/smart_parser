import declarations.models as models
from declarations.serializers import TSectionPassportFactory
from declarations.documents import stop_elastic_indexing

from django.core.management import BaseCommand
from django_elasticsearch_dsl.management.commands.search_index import Command as ElasticManagement
import logging
import pymysql
import os

def setup_logging(logfilename="copy_person.log"):
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


def copy_human_merges(logger, human_persons):
    mergings_count = 0
    logger.info("set person_id to sections")
    cnt = 0
    for section_id, factory in TSectionPassportFactory.get_all_passport_factories():
        cnt += 1
        if (cnt % 10000) == 0:
            logger.debug("number processed sections = {}".format(cnt))
        person_id = factory.search_by_passports(human_persons)[0]
        if person_id is not None:
            person = models.Person.objects.get_or_create(id=person_id)[0]
            section = models.Section.objects.get(id=section_id)
            logger.debug("connect section {} to person {}".format(section_id, person_id))

            person.declarator_person_id = person_id
            if person.person_name is None or len(person.person_name) < len(section.person_name):
                person.person_name = section.person_name
            person.save()

            section.person = person
            section.save()
            mergings_count += 1
    logger.info("set human person id to {} records".format(mergings_count))


class Command(BaseCommand):
    help = 'copy person id from declarator to disclosures'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

    def handle(self, *args, **options):
        logger = setup_logging()
        db_connection = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                                        unix_socket="/var/run/mysqld/mysqld.sock")
        logger.info("stop_elastic_indexing")
        stop_elastic_indexing()
        factories = TSectionPassportFactory.get_all_passports_from_declarator_with_person_id(db_connection)
        human_persons = TSectionPassportFactory.get_all_passports_dict(factories)
        db_connection.close()
        copy_human_merges(logger, human_persons)

        logger.info("rebuild elastic search for person")
        ElasticManagement().handle(action="rebuild", models=["declarations.Person"], force=True, parallel=True,
                                   count=True)
        logger.info("all done")

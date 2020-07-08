import declarations.models as models
from declarations.documents import stop_elastic_indexing

from django.core.management import BaseCommand
from django_elasticsearch_dsl.management.commands.search_index import Command as ElasticManagement
import logging
import pymysql
import os
import gc


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


def copy_human_merge(logger, section, person_id):
    person = models.Person.objects.get_or_create(id=person_id)[0]
    logger.debug("connect section {} to person {}".format(section.id, person_id))
    person.declarator_person_id = person_id
    if person.person_name is None or len(person.person_name) < len(section.person_name):
        person.person_name = section.person_name
    person.save()
    section.person = person
    section.dedupe_score = None
    section.save()


def build_key(document_id, fio, income_main):
    if income_main is None:
        income_main = 0
    return "{}_{}_{}".format(document_id, fio.lower(), int(income_main))


def get_all_section_from_declarator_with_person_id(connection):
    # query to declarator db
    in_cursor = connection.cursor()
    in_cursor.execute("""
                    select  s.person_id, 
                            d.id, 
                            floor(i.size),
                            s.original_fio, 
                            CONCAT(p.family_name, " ", p.name, " ", p.patronymic)
                    from declarations_section s
                    inner join declarations_person p on p.id = s.person_id
                    inner join declarations_document d on s.document_id = d.id
                    left join declarations_income i on i.section_id = s.id
                    where s.person_id is not null
                          and i.relative_id is null;

    """)
    props_to_person_id = dict()
    for person_id, document_id, income_main, original_fio, person_fio in in_cursor:
        fio = original_fio
        if fio is None:
            fio = person_fio
        key1 = build_key(document_id, fio, income_main)
        if key1 in props_to_person_id:
            props_to_person_id[key1] = "AMBIGUOUS_KEY"
        else:
            props_to_person_id[key1] = person_id
        key2 = build_key(document_id, fio.split(" ")[0], income_main)
        if key2 in props_to_person_id:
            props_to_person_id[key2] = "AMBIGUOUS_KEY"
        else:
            props_to_person_id[key2] = person_id

    return props_to_person_id


def queryset_iterator(queryset, chunksize=1000):
    pk = 0
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()


class Command(BaseCommand):
    help = 'copy person id from declarator to disclosures'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

    def handle(self, *args, **options):
        logger = setup_logging()
        db_connection = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                                        unix_socket="/var/run/mysqld/mysqld.sock")
        prop_to_person = get_all_section_from_declarator_with_person_id(db_connection)
        #with open("debug.dump", "w", encoding="utf8") as outp:
        #    json.dump( prop_to_person, outp, indent=4, ensure_ascii=False)
        logger.info("found {} mergings in declarator".format(len(prop_to_person)))
        logger.info("stop_elastic_indexing")
        stop_elastic_indexing()
        cnt = 0
        mergings_count = 0
        for section in queryset_iterator(models.Section.objects.filter(spjsonfile__declarator_document_id__isnull=False)):
            cnt += 1
            if (cnt % 10000) == 0:
                logger.debug("number processed sections = {}".format(cnt))

            main_income = 0
            for i in section.income_set.all():
                if i.relative == models.Relative.main_declarant_code:
                    main_income = i.size
            key1 = build_key(section.spjsonfile.declarator_document_id, section.person_name, main_income)
            words = section.person_name.split()
            if len(words) == 0:
                logger.error("section {} fio={} cannot find surname(first word)".format(section.id, section.person_name))
                key2 = key1
            else:
                key2 = build_key(section.spjsonfile.declarator_document_id, words[0], main_income)
            person_id1 = prop_to_person.get(key1)
            person_id2 = prop_to_person.get(key2)
            if person_id1 is None and person_id2 is None:
                logger.debug("section {} fio={} cannot be found in declarator".format(section.id, section.person_name))
            elif person_id1 is not None and person_id1 != "AMBIGUOUS_KEY":
                copy_human_merge(logger, section, person_id1)
                mergings_count += 1
            elif person_id2 is not None and person_id2 != "AMBIGUOUS_KEY":
                copy_human_merge(logger, section, person_id2)
                mergings_count += 1
            else:
                logger.debug("section {} fio={} is ambiguous".format(section.id, section.person_name))

        logger.info("set human person id to {} records".format(mergings_count))

        logger.info("rebuild elastic search for person")
        ElasticManagement().handle(action="rebuild", models=["declarations.Person"], force=True, parallel=True,
                                   count=True)
        logger.info("all done")

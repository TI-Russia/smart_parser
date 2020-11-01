import declarations.models as models
from declarations.documents import stop_elastic_indexing, start_elastic_indexing
from django.core.management import BaseCommand
from django_elasticsearch_dsl.management.commands.search_index import Command as ElasticManagement
import logging
import pymysql
import os
import gc
import json
from declarations.management.commands.permalinks import TPermaLinksDB


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


def build_section_passport(document_id, fio, income_main):
    if income_main is None:
        income_main = 0
    return "{}_{}_{}".format(document_id, fio.lower(), int(income_main))


def get_all_section_from_declarator_with_person_id():
    # query to declarator db
    db_connection = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                    unix_socket="/var/run/mysqld/mysqld.sock")
    in_cursor = db_connection.cursor()
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
        key1 = build_section_passport(document_id, fio, income_main)
        if key1 in props_to_person_id:
            props_to_person_id[key1] = "AMBIGUOUS_KEY"
        else:
            props_to_person_id[key1] = person_id
        key2 = build_section_passport(document_id, fio.split(" ")[0], income_main)
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
        self.primary_keys_builder = None
        self.logger = None

    def add_arguments(self, parser):
        parser.add_argument(
                '--read-person-from-json',
            dest='read_person_from_json',
            default=None,
            help='read person info  from json for testing'
        )
        parser.add_argument(
            '--permanent-links-db',
            dest='permanent_links_db',
            required=True
        )

    def open_permalinks_db(self):
        self.primary_keys_builder = TPermaLinksDB(self.options['permanent_links_db'])
        self.primary_keys_builder.open_db_read_only()

    def update_primary_keys(self):
        self.primary_keys_builder.close()
        self.primary_keys_builder.update_person_records_count_and_close()

    def build_passport_to_person_id_mapping_from_declarator(self):
        if self.options.get('read_person_from_json') is not None:
            with open(self.options.get('read_person_from_json'), "r", encoding="utf8") as inpf:
                return json.load(inpf)
        else:
            return get_all_section_from_declarator_with_person_id()

    def copy_human_merge(self, section, declarator_person_id):
        # we think that person ids in declarator db are stable
        person = models.Person(declarator_person_id=declarator_person_id)
        person.id = self.primary_keys_builder.get_record_id(person)
        self.logger.debug("connect section {} to person {}, declarator_person_id={}".format(
            section.id, person.id, declarator_person_id))
        if person.person_name is None or len(person.person_name) < len(section.person_name):
            person.person_name = section.person_name
        person.save()
        section.person = person
        section.dedupe_score = None
        section.save()

    def process_section(self, section, section_passports):
        main_income = 0
        for i in section.income_set.all():
            if i.relative == models.Relative.main_declarant_code:
                main_income = i.size
        checked_results = set()
        for declaration_info in section.source_document.declarator_file_reference_set.all():
            key1 = build_section_passport(declaration_info.declarator_document_id, section.person_name, main_income)
            checked_results.add(section_passports.get(key1))
            words = section.person_name.split()
            if len(words) > 0:
                key2 = build_section_passport(declaration_info.declarator_document_id, words[0], main_income)
                checked_results.add(section_passports.get(key2))
            else:
                self.logger.error(
                    "section {} fio={} cannot find surname(first word)".format(section.id, section.person_name))

        if len(checked_results) == 1 and None in checked_results:
            self.logger.debug("section {} fio={} cannot be found in declarator".format(section.id, section.person_name))
        else:
            for person_id in checked_results:
                if person_id is not None and person_id != "AMBIGUOUS_KEY":
                    self.copy_human_merge(section, person_id)
                    return True
            self.logger.debug("section {} fio={} is ambiguous".format(section.id, section.person_name))
        return False

    def handle(self, *args, **options):
        self.logger = setup_logging()
        self.options = options
        self.open_permalinks_db()
        section_passports = self.build_passport_to_person_id_mapping_from_declarator()
        self.logger.info("found {} merges in declarator".format(len(section_passports)))
        self.logger.info("stop_elastic_indexing")
        stop_elastic_indexing()
        cnt = 0
        merge_count = 0
        for section  in queryset_iterator(models.Section.objects):
            cnt += 1
            if (cnt % 10000) == 0:
                self.logger.debug("number processed sections = {}".format(cnt))
            if self.process_section(section, section_passports):
                merge_count += 1

        self.logger.info("set human person id to {} records".format(merge_count))

        self.logger.info("rebuild elastic search for person")
        ElasticManagement().handle(action="rebuild", models=["declarations.Person"], force=True, parallel=True,
                                   count=True)
        
        start_elastic_indexing()
        self.update_primary_keys()
        self.logger.info("all done")

CopyPersonIdCommand=Command

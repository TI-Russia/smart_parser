from declarations.documents import stop_elastic_indexing
from declarations.management.commands.permalinks import TPermaLinksDB
import declarations.models as models
from .random_forest_adapter import TDeduplicationObject, TFioClustering, TMLModel

import logging
from django.core.management import BaseCommand
import sys
import json
from collections import defaultdict


def setup_logging(logfilename):
    if logfilename is None:
        logfilename = "generate_dedupe_pairs.log"
    logger = logging.getLogger("generate_dedupe_pairs")
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    return logger


class Command(BaseCommand):
    help = ''

    def add_arguments(self, parser):
        parser.add_argument(
            '--surname-bounds',
            dest='surname_bounds',
            default=None,
            help='[l,b], take records where person_name >=l and person_name < b',
        )
        parser.add_argument(
            '--print-family-prefixes',
            dest='print_family_prefixes',
            default=False,
            action="store_true",
            help='print family prefixes and exit',
        )
        parser.add_argument(
            '--ml-model-file',
            dest='model_file',
        )
        parser.add_argument(
            '--threshold',
            dest='threshold',
            type=float,
        )
        parser.add_argument(
            '--result-pairs-file',
            dest='result_pairs_file',
            help='',
        )
        parser.add_argument(
            '--rebuild',
            dest='rebuild',
            action="store_true",
            default=False,
            help='rebuild old persom, declaration pairs',
        )
        parser.add_argument(
            '--dump-dedupe-objects-file',
            dest='dump_dedupe_objects_file',
            help='',
        )
        parser.add_argument(
            '--write-to-db',
            dest='write_to_db',
            action='store_true',
            default=False,
            help='write back to DB',
        )
        parser.add_argument(
            '--permanent-links-db',
            dest='permanent_links_db',
            required=True
        )
        parser.add_argument(
            '--fake-dedupe',
            dest='fake_dedupe',
            required=False,
            help='create one person for all sections without dedupe (test purpose)'
        )
        parser.add_argument(
            '--logfile',
            dest='logfile',
            required=False,
            help='set logfile name'
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.ml_model = None
        self.options = None
        self.logger = None
        self.permalinks_db = None
        self.rebuild = False
        self.threshold = 0
        self.cluster_by_minimal_fio = defaultdict(list)
        self.section_cache = dict()

    def init_options(self, options):
        self.logger = setup_logging(options.get('logfile'))
        self.options = options
        self.rebuild = options.get('rebuild', False)
        if self.rebuild and not options['write_to_db']:
            self.logger.info("please add --write-to-db  option if you use --rebuild")
        self.permalinks_db = TPermaLinksDB(options['permanent_links_db'])
        self.permalinks_db.open_db_read_only()
        if options.get('threshold', 0) != 0:
            self.threshold = options.get('threshold')
        else:
            self.logger.info('Warning! Threshold is not set. Is it just a test?')

    def filter_table(self, model_type, lower_bound, upper_bound):
        records = model_type.objects
        if lower_bound != '':
            records = records.filter(person_name__gte=lower_bound)
        if upper_bound != '':
            records = records.filter(person_name__lt=upper_bound)
        records_count = records.count()
        self.logger.info("Start reading {} records from {}... ".format(records_count, model_type._meta.db_table))
        return records

    def read_sections(self, lower_bound, upper_bound):
        sections = self.filter_table(models.Section, lower_bound, upper_bound)
        if not self.rebuild:
            sections = sections.filter(person=None)
        cnt = 0
        take_sections_with_empty_income = self.options.get('take_sections_with_empty_income', False)
        for s in sections.all():
            if s.person is not None:
                if s.person.declarator_person_id is not None:
                    # this merging was copied from declarator, do not touch it
                    continue
                else:
                    if self.rebuild:
                        # this merging was created by the previous dedupe run
                        s.dedupe_score = None
                        s.person_id = None
                        s.save() # do it to disable constraint delete
            o = TDeduplicationObject().initialize_from_section(s)
            if not o.fio.is_resolved:
                self.logger.debug("ignore section id={} person_name={}, cannot find family name".format(s.id, s.person_name))
                continue
            if not take_sections_with_empty_income and o.average_income == 0:
                self.logger.debug("ignore section id={} person_name={}, no income or zero-income".format(s.id, s.person_name))
                continue
            self.section_cache[s.id] = s
            self.cluster_by_minimal_fio[o.fio.build_fio_with_initials()].append(o)
            cnt += 1
            if cnt % 10000 == 0:
                self.logger.info("Read {} records from section table".format(cnt))
        self.logger.info("Read {0} records from section table".format(cnt))

    def read_people(self, lower_bound, upper_bound):
        persons = self.filter_table(models.Person, lower_bound, upper_bound)
        cnt = 0
        deleted_cnt = 0
        for p in persons.all():
            if self.rebuild and p.declarator_person_id is None:
                # the record was created by the previous deduplication run
                p.delete()
                deleted_cnt += 1
            else:
                o = TDeduplicationObject().initialize_from_person(p)
                if len(o.years) > 0:
                    self.cluster_by_minimal_fio[o.fio.build_fio_with_initials()].append(o)
                cnt += 1
                if cnt % 1000 == 0:
                    self.logger.info("Read {} records from person table".format(cnt))
        self.logger.info("Read {} records from person table".format(cnt))
        if deleted_cnt > 0:
            self.logger.info("Deleted {} records from person table".format(deleted_cnt))

    def get_all_leaf_objects(self):
        for l in self.cluster_by_minimal_fio.values():
            for o in l:
                yield o

    def fill_dedupe_data(self, lower_bound, upper_bound):
        self.cluster_by_minimal_fio = defaultdict(list)

        self.read_sections(lower_bound, upper_bound)
        self.read_people(lower_bound, upper_bound)

        dump_file_name = self.options.get("dump_dedupe_objects_file")
        if dump_file_name:
            with open(dump_file_name, "w", encoding="utf-8") as of:
                for o in self.get_all_leaf_objects():
                    js = json.dumps(o.to_json(), ensure_ascii=False)
                    of.write(js + "\n")

    def write_results_to_file(self, clusters, dump_stream):
        self.logger.info('{} clusters generated'.format(len(clusters)))
        for cluster_id, items in clusters.items():
            dump_stream.write("cluster {}\n".format(cluster_id))
            for obj, distance in items:
                dump_stream.write("\t{} {} {} {}\n".format(
                    obj.record_id,
                    1.0 - distance,
                    obj.person_name,
                    min(obj.years)))

    def link_section_to_person(self, section, person, distance):
        if section.person_id == person.id:
            #dedupe score is not set to these records, they are from declarator
            return
        section.person_id = person.id
        section.dedupe_score = 1.0 - distance
        section.save()
        if len(person.person_name) < len(section.person_name):
            person.person_name = section.person_name
            person.save()

    def link_sections_to_a_new_person(self, sections, section_distances):
        assert len(section_distances) == len(sections)
        person_variants = defaultdict(int)
        for section in sections:
            person_id = self.permalinks_db.get_person_id_by_section(section)
            if person_id is not None:
                person_variants[person_id] += 1

        if len(person_variants) > 0:
            max_person_id_count, max_person_id = sorted( list( (v, k) for (k, v) in person_variants.items()))[-1]
            section_count_in_old_cluster = self.permalinks_db.get_section_count_by_person_id(max_person_id)
            if section_count_in_old_cluster is not None and max_person_id_count * 2 > section_count_in_old_cluster:
                self.logger.debug("use old person.id, max_person_id={}, section_count_in_old_cluster={}, max_person_id_count={}".format(
                    max_person_id, max_person_id_count, section_count_in_old_cluster
                ))
                person_id = max_person_id

        if person_id is None:
            person_id = self.permalinks_db.get_new_id(models.Person)
        person = models.Person(id=person_id)
        person.save()

        for (section, distance) in zip(sections,section_distances):
            self.link_section_to_person(section, person, distance)

    def write_results_to_db(self, clusters):
        for cluster_id, items in clusters.items():
            self.logger.debug("process cluster {}".format(cluster_id))
            person_ids = list()
            sections = list()
            section_distances = list()
            for obj, distance in items:
                if obj.record_id.source_table == TDeduplicationObject.PERSON:
                    person_ids.append(obj.record_id.id)
                else:
                    section = self.section_cache[obj.record_id.id]
                    sections.append(section)
                    section_distances.append(distance)
            if len(person_ids) == 0:
                self.link_sections_to_a_new_person(sections, section_distances)
            elif len(person_ids) == 1:
                person = models.Person.objects.get(id=person_ids[0])
                for section, distance in zip(sections, section_distances):
                    self.link_section_to_person(section, person, distance)
            else:
                self.logger.error("a cluster with two people found, I do not know what to do")

    def get_family_name_bounds(self):
        if self.options.get('surname_bounds') is not None:
            yield self.options.get('surname_bounds').split(',')
        else:
            all_borders = ',А,Б,БП,В,Г,ГП,Д,Е,Ж,ЖР,З,И,К,КИ,КП,КС,Л,М,МН,Н,О,П,ПН,Р,С,СН,Т,ТП,У,Ф,Х,Ц,Ч,Ш,ШП,Щ,Э,Ю,Я,'.split(',')
            for x in range(1, len(all_borders)):
                yield all_borders[x-1], all_borders[x]

    def load_dedupe_model(self):
        if not self.options.get("fake_dedupe", False):
            self.logger.info('read ml model from {}'.format(self.options["model_file"]))
            self.ml_model = TMLModel(self.options["model_file"])

    def cluster_sections(self):
        for _, leaf_clusters in self.cluster_by_minimal_fio.items():
            clustering = TFioClustering(leaf_clusters, self.ml_model, self.threshold)
            clustering.cluster()
            yield clustering.clusters

    def cluster_sections_by_minimal_fio(self):
        if self.options.get("fake_dedupe", False):
            # all records in one cluster
            c = defaultdict(list)
            c[0] = [(i, 0.5) for i in self.get_all_leaf_objects()]
            yield c
        else:
            all_objects_count = sum(len(v) for v in self.cluster_by_minimal_fio.values())
            self.logger.info('Clustering {} objects with threshold={}, len(self.cluster_by_minimal_fio) = {}'.format(
                all_objects_count, self.threshold, len(self.cluster_by_minimal_fio)))
            for c in self.cluster_sections():
                yield c

    def handle(self, *args, **options):
        self.init_options(options)
        if options.get('print_family_prefixes'):
            for lower_bound, upper_bound in self.get_family_name_bounds():
                sys.stdout.write("{},{}\n".format(lower_bound, upper_bound))
            return
        self.logger.info('surname bounds are {}'.format(options.get('surname_bounds', "")))
        stop_elastic_indexing()
        self.load_dedupe_model()
        dump_stream = None
        dump_file_name = self.options.get("result_pairs_file")
        if dump_file_name:
            dump_stream = open(dump_file_name, "w", encoding="utf8")
            self.logger.debug('write result pairs to {}\n'.format(dump_file_name))

        for lower_bound, upper_bound in self.get_family_name_bounds():
            self.logger.info("lower_bound={}, upper_bound={}".format(lower_bound, upper_bound))
            self.fill_dedupe_data(lower_bound, upper_bound)
            for clusters_for_one_fio in self.cluster_sections_by_minimal_fio():
                if dump_stream is not None:
                    self.write_results_to_file(clusters_for_one_fio, dump_stream)
                if options['write_to_db']:
                    self.write_results_to_db(clusters_for_one_fio)

        if dump_stream is not None:
            dump_stream.close()

RunDedupe=Command

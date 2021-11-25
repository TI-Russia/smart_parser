from declarations.permalinks import TPermaLinksPerson
import declarations.models as models
from .random_forest_adapter import TDeduplicationObject, TFioClustering, TMLModel
from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand
import sys
import json
from collections import defaultdict
import itertools
from django.db import connection
import re


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
            '--input-dedupe-objects',
            dest='input_dedupe_objects',
            help='read objects that were written by option --dump-dedupe-objects-file',
        )
        parser.add_argument(
            '--recreate-sections-and-persons',
            dest='recreate_db',
            help='create fake sections and persons that are written in --input-dedupe-objects',
        )

        parser.add_argument(
            '--write-to-db',
            dest='write_to_db',
            action='store_true',
            default=False,
            help='write back to DB',
        )
        parser.add_argument(
            '--permalinks-folder',
            dest='permalinks_folder',
            required=True
        )
        parser.add_argument(
            '--fake-dedupe',
            dest='fake_dedupe',
            required=False,
            help='create one person for all sections without dedupe (test purpose)'
        )
        parser.add_argument(
            '--separate-sections',
            dest='separate_sections',
            required=False,
            help='put all sections in a separate cluster (test purpose)'
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
        self.logger = setup_logging(log_file_name=options.get('logfile'))
        self.options = options
        self.rebuild = options.get('rebuild', False)
        if self.rebuild and not options['write_to_db']:
            self.logger.info("please add --write-to-db  option if you use --rebuild")
        self.permalinks_db = TPermaLinksPerson(options['permalinks_folder'])
        self.permalinks_db.open_db_read_only()
        if options.get('threshold', 0) != 0:
            self.threshold = options.get('threshold')
        else:
            self.logger.info('Warning! Threshold is not set. Is it just a test?')

    def filter_table(self, model_type, lower_bound, upper_bound):
        #By default, string comparisons in sql are case insensitive because strings are non-binary.
        records = model_type.objects
        if lower_bound != '':
            records = records.filter(person_name__gte=lower_bound)
        if upper_bound != '':
            records = records.filter(person_name__lt=upper_bound)
        records_count = records.count()
        self.logger.info("Start reading {} records from {}... ".format(records_count, model_type._meta.db_table))
        return records

    def read_sections(self, lower_bound, upper_bound):
        sections = self.filter_table(models.Section, lower_bound, upper_bound)\

        # there are sections with person_id != null, person_id was set by  copy_person_id.py,
        # we need these records to build valid clusters
        cnt = 0
        take_sections_with_empty_income = self.options.get('take_sections_with_empty_income', False)
        trace = (self.options.get('verbosity', 0) == 3)
        for s in sections.all():
            o = TDeduplicationObject().initialize_from_section(s)
            if not o.fio.is_resolved:
                self.logger.debug("ignore section id={} person_name={}, cannot find family name".format(s.id, s.person_name))
                continue
            if not take_sections_with_empty_income and o.average_income == 0:
                self.logger.debug("ignore section id={} person_name={}, no income or zero-income".format(s.id, s.person_name))
                continue
            self.section_cache[s.id] = s
            if trace:
                self.logger.debug("read section id = {}".format(s.id))
            self.cluster_by_minimal_fio[o.fio.build_fio_with_initials()].append(o)
            cnt += 1
            if cnt % 10000 == 0:
                self.logger.info("Read {} records from section table".format(cnt))
        self.logger.info("Read {0} records from section table".format(cnt))

    def read_people(self, lower_bound, upper_bound):
        persons = self.filter_table(models.Person, lower_bound, upper_bound)
        cnt = 0
        trace = (self.options.get('verbosity', 0) == 3)
        for p in persons.all():
            o = TDeduplicationObject().initialize_from_person(p)
            if len(o.years) > 0:
                self.cluster_by_minimal_fio[o.fio.build_fio_with_initials()].append(o)
            else:
                self.logger.debug("skip person id={}, because this record has no related sections with"
                                  " defined income years".format(p.id))
            if trace:
                self.logger.debug("read person id = {}".format(p.id))
            cnt += 1
            if cnt % 1000 == 0:
                self.logger.info("Read {} records from person table".format(cnt))
        self.logger.info("Read {} records from person table".format(cnt))

    def get_all_leaf_objects(self):
        for l in self.cluster_by_minimal_fio.values():
            for o in l:
                yield o

    def filter_sql_by_person_name(self, sql, lower_bound, upper_bound):
        # By default, string comparisons in sql are case insensitive because strings are non-binary.
        if lower_bound != '':
            sql += " and person_name >= '{}' ".format(lower_bound)
        if upper_bound != '':
            sql += " and person_name <  '{}' ".format(upper_bound)
        return sql

    def delete_person_ids_from_previous_deduplication(self, lower_bound, upper_bound):
        sql = self.filter_sql_by_person_name("update declarations_section set " \
              "person_id=null, dedupe_score=null " \
              "where dedupe_score is not null ", lower_bound, upper_bound)

        if lower_bound != '':
            assert upper_bound != ''
            sql += ""
        self.logger.debug(sql)
        with connection.cursor() as cursor:
            cursor.execute(sql)

        sql = self.filter_sql_by_person_name("delete from declarations_person " \
                        "where declarator_person_id is null", lower_bound, upper_bound)
        self.logger.debug(sql)
        with connection.cursor() as cursor:
            cursor.execute(sql)

    def read_dumped_objects(self, file_name):
        if self.options.get('recreate_db'):
            assert models.Section.objects.count() == 0
        with open(file_name) as inp:
            for line in inp:
                js = json.loads(line)
                o = TDeduplicationObject().from_json(js)
                if self.options.get('recreate_db'):
                    if o.record_id.source_table == TDeduplicationObject.SECTION:
                        assert len(o.offices) == 1
                        s = models.Section(id=o.record_id.id, office_id=list(o.offices)[0])
                        self.section_cache[o.record_id.id] = s
                        s.save()
                    else:
                        models.Person(id=o.record_id.id).save()
                self.cluster_by_minimal_fio[o.fio.build_fio_with_initials()].append(o)

    def dump_dedupe_objects(self, dump_file_name):
        with open(dump_file_name, "w", encoding="utf-8") as of:
            for o in self.get_all_leaf_objects():
                js = json.dumps(o.to_json(), ensure_ascii=False)
                of.write(js + "\n")

    def fill_dedupe_data(self, lower_bound, upper_bound):
        self.cluster_by_minimal_fio = defaultdict(list)
        if self.rebuild:
            self.delete_person_ids_from_previous_deduplication(lower_bound, upper_bound)
        if self.options.get('input_dedupe_objects') is not None:
            self.read_dumped_objects(self.options.get('input_dedupe_objects'))
        else:
            self.read_sections(lower_bound, upper_bound)
            self.read_people(lower_bound, upper_bound)

        dump_file_name = self.options.get("dump_dedupe_objects_file")
        if dump_file_name:
            self.dump_dedupe_objects(dump_file_name)

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
        if section.person_id is not None and section.dedupe_score is None:
            #these person_id's came from declarator, do not touch them
            self.logger.debug("skip setting person_id={} to section (id={}, person_id={}), because it is from declarator".format(
                    person.id, section.id, section.person_id))
            return
        self.logger.debug("link section {} to person {}".format(section.id, person.id))
        section.person_id = person.id
        section.dedupe_score = 1.0 - distance
        section.save()
        if len(person.person_name) < len(section.person_name):
            person.person_name = section.person_name
            person.save()

    def link_sections_to_a_new_person(self, sections, section_distances, person_id):
        assert len(section_distances) == len(sections)
        if person_id is None:
            person_id = self.permalinks_db._get_new_id()
            self.logger.debug("create new person.id: {}".format(person_id))
        else:
            self.logger.debug("use old person.id: {}".format(person_id))

        try:
            person = models.Person.objects.get(id=person_id)
            #reuse person record from declarator
            if person.declarator_person_id is None:
                self.logger.error("Warning! Reuse existing person_id = {} for different sections (cluster), it could happen"
                                  "if this person_id was used for different person created by copy_person_id.py "
                                  "but should not happen if declarator_person_id is None. ".format(person_id))
        except models.Person.DoesNotExist as exp:
            #create new person record
            person = models.Person(id=person_id)
            person.save()

        for (section, distance) in zip(sections,section_distances):
            self.link_section_to_person(section, person, distance)

    def _get_old_clustering(self, clusters):
        old_person_to_new_sections = defaultdict(list)
        for cluster_id, items in clusters.items():
            section_to_person = list()
            found_person = False
            for obj, distance in items:
                if obj.record_id.source_table == TDeduplicationObject.SECTION:
                    section_id = obj.record_id.id
                    person_id = self.permalinks_db.get_person_id_by_section_id(section_id)
                    if person_id is not None:
                        section_to_person.append((section_id, person_id))
                else:
                    # a person is already in this cluster, use it
                    found_person = True
                    break
            if not found_person:
                for (section_id, person_id) in section_to_person:
                    old_person_to_new_sections[person_id].append((cluster_id, section_id))
        return old_person_to_new_sections

    def build_cluster_to_old_person_id(self, clusters):
        old_person_to_sections = self._get_old_clustering(clusters)

        intersections = list()
        for person_id, sections in old_person_to_sections.items():
            # take always the cluster with that the minimal section_id
            min_section = min(section for section, _ in sections)
            for cluster_id, items in itertools.groupby(sections, lambda x: x[0]):
                intersection_size = len(list(items))
                intersections.append((-intersection_size, -min_section, person_id, cluster_id))
        intersections = sorted(intersections)
        used_person_ids = set()
        used_cluster_ids = set()
        new_to_old_clusters = dict()
        for _, _, person_id, cluster_id in intersections:
            already = (person_id in used_person_ids) or (cluster_id in used_cluster_ids)
            used_person_ids.add(person_id)
            used_cluster_ids.add(cluster_id)
            if not already:
                new_to_old_clusters[cluster_id] = person_id
        return new_to_old_clusters

    def write_results_to_db(self, clusters):
        clusters_to_old_person_ids = self.build_cluster_to_old_person_id(clusters)

        for cluster_id, items in clusters.items():
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
                self.link_sections_to_a_new_person(sections, section_distances,
                                                   clusters_to_old_person_ids.get(cluster_id))
            elif len(person_ids) == 1:
                person = models.Person.objects.get(id=person_ids[0])
                for section, distance in zip(sections, section_distances):
                    self.link_section_to_person(section, person, distance)
            else:
                left_sections = ",".join((str(section.id) for section in sections))
                persons = ",".join((str(id) for id in person_ids))
                self.logger.debug("a cluster with two people found, I do not know what to do".format(left_sections))
                self.logger.debug("  cluster sections: ".format(left_sections))
                self.logger.debug("  cluster persons: ".format(persons))

    def get_person_name_baskets(self):
        if self.options.get('surname_bounds') is not None:
            yield self.options.get('surname_bounds').split(',')
        else:
            # By default, string comparisons in sql are case insensitive because strings are non-binary.
            sql = """
                    select substring(upper(person_name), 1, 3) as a, count(id) 
                    from declarations_section
                    group by a
                    order by a 
                   """;
            borders = list([''])
            with connection.cursor() as cursor:
                cursor.execute(sql)
                cnt = 0
                accum = 0
                last_trigram = None
                for trigram, trigram_count in cursor:
                    cnt += trigram_count
                    if accum + trigram_count > 50000 and last_trigram is not None:
                        borders.append(last_trigram)
                        accum = 0
                    accum += trigram_count
                    if re.search(r'[\s/.,"\\:-]', trigram) is None:
                        last_trigram = trigram
                assert cnt == models.Section.objects.count()
            borders.append('')
            for x in range(1, len(borders)):
                yield borders[x-1], borders[x]

    def load_dedupe_model(self):
        if not self.options.get("fake_dedupe", False):
            self.logger.info('read ml model from {}'.format(self.options["model_file"]))
            self.ml_model = TMLModel(self.options["model_file"])

    def cluster_sections(self):
        for fio, leaf_clusters in self.cluster_by_minimal_fio.items():
            self.logger.debug("cluster inside for {}: {} sections".format(fio, len(leaf_clusters)))
            clustering = TFioClustering(self.logger, leaf_clusters, self.ml_model, self.threshold)
            clustering.cluster()
            yield clustering.clusters

    def cluster_sections_by_minimal_fio(self):
        if self.options.get("fake_dedupe", False):
            if self.options.get("separate_sections", False):
                # each record to a separate cluster
                c = defaultdict(list)
                k = 0
                for i in self.get_all_leaf_objects():
                    c[k] = [(i, 0.1)]
                    k += 1
                yield c
            else:
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
            for lower_bound, upper_bound in self.get_person_name_baskets():
                sys.stdout.write("{},{}\n".format(lower_bound, upper_bound))
            return
        self.logger.info('surname bounds are {}'.format(options.get('surname_bounds', "")))
        self.load_dedupe_model()
        dump_stream = None
        dump_file_name = self.options.get("result_pairs_file")
        if dump_file_name:
            dump_stream = open(dump_file_name, "w", encoding="utf8")
            self.logger.debug('write result pairs to {}\n'.format(dump_file_name))

        for lower_bound, upper_bound in self.get_person_name_baskets():
            self.logger.info("lower_bound={}, upper_bound={}".format(lower_bound, upper_bound))
            self.fill_dedupe_data(lower_bound, upper_bound)
            for clusters_for_one_fio in self.cluster_sections_by_minimal_fio():
                if dump_stream is not None:
                    self.write_results_to_file(clusters_for_one_fio, dump_stream)
                if options['write_to_db']:
                    self.write_results_to_db(clusters_for_one_fio)

        if dump_stream is not None:
            dump_stream.close()
        self.logger.debug("all done")


RunDedupe=Command

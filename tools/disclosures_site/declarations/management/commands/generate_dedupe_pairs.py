from __future__ import unicode_literals
import dedupe
import logging
from datetime import datetime
from django.core.management import BaseCommand
from .dedupe_adapter import TPersonFields, dedupe_object_reader, dedupe_object_writer, describe_dedupe, \
    get_pairs_from_clusters
import sys
from declarations.documents import stop_elastic_indexing, start_elastic_indexing
from declarations.management.commands.permalinks import TPermaLinksDB
import declarations.models as models


def setup_logging(logfilename="generate_dedupe_pairs.log"):
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
            '--verbose',
            dest='verbose',
            type=int,
            help='set verbosity, default is DEBUG',
            default=0
        )
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
            '--num-cores',
            dest='num_cores',
            type=int,
            default=1,
            help='num cores for dedupe',
        )
        parser.add_argument(
            '--dedupe-model-file',
            dest='model_file',
            default="dedupe.info",
            help='dedupe settings (trained model)',
        )
        parser.add_argument(
            '--dedupe-trained-other-settings',
            dest='dedupe_aux_json',
            default="dedupe_aux.json",
            help='a file to write the trained threshold',
        )
        parser.add_argument(
            '--threshold',
            dest='threshold',
            default=0.0,
            type=float,
            help='a custom threshold',
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
            '--input-dedupe-objects',
            dest='input_dedupe_objects',
            help='',
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

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.dedupe = None
        self.dedupe_objects = None
        self.options = None
        self.logger = setup_logging()
        self.primary_keys_builder = None
        self.rebuild = False

    def init_options(self, options):
        self.options = options
        self.rebuild = options.get('rebuild', False)
        log_level = logging.WARNING
        if options.get("verbose"):
            if options.get("verbose") == 1:
                log_level = logging.INFO
            elif options.get("verbose") >= 2:
                log_level = logging.DEBUG
        self.logger.setLevel(log_level)
        if self.rebuild and not options['write_to_db']:
            self.logger.info("please add --write-to-db  option if you use --rebuild")
        self.primary_keys_builder = TPermaLinksDB(options['permanent_links_db'])
        self.primary_keys_builder.open_db_read_only()
        self.primary_keys_builder.create_sql_sequences()

    def read_sections(self, lower_bound, upper_bound):
        sections = models.Section.objects
        if lower_bound != '':
            sections = sections.filter(person_name__gte=lower_bound)
        if upper_bound != '':
            sections = sections.filter(person_name__lt=upper_bound)
        if not self.rebuild:
            sections = sections.filter(person=None)
        sections_count = sections.count()
        self.logger.info("Start reading {} sections from DB... ".format(sections_count))
        cnt = 0
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
            k, v = TPersonFields(None, s).get_dedupe_id_and_object()
            assert k is not None
            if len(v['family_name']) == 0:
                continue # ignore sections with broken person names, because dedupe fails
            self.dedupe_objects[k] = v
            cnt += 1
            if cnt % 10000 == 0:
                self.logger.info("Read {} records from section table".format(cnt))
        self.logger.info("Read {0} records from section table".format(cnt))

    def read_people(self, lower_bound, upper_bound):
        persons = models.Person.objects
        if lower_bound != '':
            persons = persons.filter(section__person_name__gte=lower_bound)
        if upper_bound != '':
            persons = persons.filter(section__person_name__lt=upper_bound)
        persons = persons.distinct()
        persons_count = persons.count()
        self.logger.info("Start reading {} people records from DB...".format(persons_count))
        cnt = 0
        deleted_cnt = 0
        for p in persons.all():
            if self.rebuild and p.declarator_person_id is None:
                # the record was created by the previous deduplication run
                p.delete()
                deleted_cnt += 1
            else:
                #p.refresh_from_db()
                k, v = TPersonFields(p).get_dedupe_id_and_object()
                if k is None:
                    continue
                    # no sections for this person, ignore this person
                self.dedupe_objects[k] = v
            cnt += 1
            if cnt % 1000 == 0:
                self.logger.info("Read {} records from person table".format(cnt))
        self.logger.info("Read {} records from person table".format(cnt))
        if deleted_cnt > 0:
            self.logger.info("Deleted {} records from person table".format(deleted_cnt))

    def fill_dedupe_data(self, lower_bound, upper_bound):
        self.dedupe_objects = {}

        input_dump_file = self.options.get("input_dedupe_objects")
        if input_dump_file is not None:
            with open(input_dump_file, "r", encoding="utf-8") as fp:
                for line in fp:
                    (k, v) = line.strip().split("\t")
                    self.dedupe_objects[str(k)] = dedupe_object_reader(v)
            return

        self.read_sections(lower_bound, upper_bound)
        self.read_people(lower_bound, upper_bound)

        self.logger.info("All objects  for dedupe = {} ".format(len(self.dedupe_objects)))

        dump_file_name = self.options.get("dump_dedupe_objects_file")
        if dump_file_name:
            with open(dump_file_name, "w", encoding="utf-8") as of:
                for k, v in self.dedupe_objects.items():
                    json_value = dedupe_object_writer(v)
                    of.write("\t".join((k, json_value)) + "\n")

    def write_results_to_file(self, clustered_dupes, dump_stream):
        self.logger.info('{} clusters generated'.format(len(clustered_dupes)))
        for id1, id2, score1, score2 in get_pairs_from_clusters(clustered_dupes):
            dump_stream.write("\t".join((id1, id2, str(score1), str(score2))) + "\n")

    def link_section_to_person(self, section, person, dedupe_score):
        section.person_id = person.id
        section.dedupe_score = dedupe_score
        section.save()
        if len(person.person_name) < len(section.person_name):
            person.person_name = section.person_name
            person.save()

    def link_sections_to_a_new_person(self, section_ids):
        person = models.Person()
        person.tmp_section_set = set(str(id) for (id, score) in section_ids)
        person.id = self.primary_keys_builder.get_record_id(person)
        person.save()
        for (section_id, score) in section_ids:
            section = models.Section.objects.get(id=section_id)
            self.link_section_to_person(section, person, score)

    def write_results_to_db(self, dedupe_clusters):
        self.logger.info('write {} results to db'.format(len(dedupe_clusters)))
        for id_set, scores in dedupe_clusters:
            self.logger.debug("process cluster {}".format(";".join((id for id in id_set))))
            person_ids = set()
            section_ids = set()
            for id, score in zip(id_set, scores):
                if id.startswith("person-"):
                    person_ids.add((int(id[len("person-"):]), score))
                else:
                    section_ids.add((int(id[len("section-"):]), score))
            if len(person_ids) == 0:
                self.link_sections_to_a_new_person(section_ids)
            elif len(person_ids) == 1:
                person_id = list(person_ids)[0][0]
                person = models.Person.objects.get(id=person_id)
                for section_id, score in section_ids:
                    section = models.Section.objects.get(id=section_id)
                    self.link_section_to_person(section, person, score)
            else:
                self.logger.error("a cluster with two people found, I do not know what to do")

    def get_family_name_bounds(self):
        if self.options.get('surname_bounds') is not None:
            yield self.options.get('surname_bounds').split(',')
        elif self.options.get("input_dedupe_objects") is not None:
            yield None, None
        else:
            all_borders = ',А,Б,БП,В,Г,ГП,Д,Е,Ж,З,И,К,КН,Л,М,МН,Н,О,П,ПН,Р,С,СН,Т,У,Ф,Х,Ц,Ч,Ш,Щ,Э,Ю,Я,'.split(',')
            for x in range(1, len(all_borders)):
                yield all_borders[x-1], all_borders[x]

    def load_dedupe_model(self):
        if not self.options.get("fake_dedupe", False):
            with open(self.options["model_file"], 'rb') as sf:
                self.logger.info('read dedupe settings from {}'.format(sf.name))
                self.dedupe = dedupe.StaticDedupe(sf, num_cores=self.options['num_cores'])
                if logging.getLogger().getEffectiveLevel() > 1:
                    describe_dedupe(self.stdout, self.dedupe)

    def cluster_with_dedupe(self):
        if self.options.get("fake_dedupe", False):
            # all records in one cluster
            ids = list(k for k in self.dedupe_objects.keys())
            return [(ids, [50]*len(ids))]
        else:
            try:
                self.logger.debug(
                    'Clustering {} objects with threshold={}.'.format(len(self.dedupe_objects), threshold))
                return self.dedupe.match(self.dedupe_objects, threshold)
            except Exception as e:
                self.logger.error(
                    'Dedupe failed for this cluster, possibly no blocks found, ignore result: {0}'.format(e))

    def handle(self, *args, **options):
        self.logger.info('Started at: {}'.format(datetime.now()))
        self.init_options(options)
        if options.get('print_family_prefixes'):
            for lower_bound, upper_bound in self.get_family_name_bounds():
                sys.stdout.write("{},{}\n".format(lower_bound, upper_bound))
            return
        stop_elastic_indexing()
        self.load_dedupe_model()

        threshold = 0
        if options.get('threshold', 0) != 0:
            threshold = options.get('threshold')
        else:
            self.logger.info('Warning! Threshold is not set. Is it just a test?')

        dump_stream = None
        dump_file_name = self.options.get("result_pairs_file")
        if dump_file_name:
            dump_stream = open(dump_file_name, "w", encoding="utf8")
            self.logger.debug(u'write result pairs to {}\n'.format(dump_file_name))

        for lower_bound, upper_bound in self.get_family_name_bounds():
            self.logger.debug("lower_bound={}, upper_bound={}".format(lower_bound, upper_bound))
            self.fill_dedupe_data(lower_bound, upper_bound)
            clustered_dupes = self.cluster_with_dedupe()
            if clustered_dupes is not None:
                if dump_stream is not None:
                    self.write_results_to_file(clustered_dupes, dump_stream)
                if options['write_to_db']:
                    self.write_results_to_db(clustered_dupes)

        if dump_stream is not None:
            dump_stream.close()
        start_elastic_indexing()

RunDedupe=Command

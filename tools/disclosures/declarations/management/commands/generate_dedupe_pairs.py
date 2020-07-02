from __future__ import unicode_literals
import dedupe
import logging
from datetime import datetime
from django.core.management import BaseCommand, CommandError
from declarations.models import Person, Section
from .dedupe_adapter import TPersonFields, dedupe_object_reader, dedupe_object_writer, describe_dedupe, \
    get_pairs_from_clusters
import sys
from declarations.documents import stop_elastic_indexing


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

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.dedupe = None
        self.dedupe_objects = None
        self.options = None
        self.logger = setup_logging()

    def init_options(self, options):
        self.options = options
        log_level = logging.WARNING
        if options.get("verbose"):
            if options.get("verbose") == 1:
                log_level = logging.INFO
            elif options.get("verbose") >= 2:
                log_level = logging.DEBUG
        self.logger.setLevel(log_level)

    def read_sections(self, lower_bound, upper_bound):
        sections = Section.objects.filter(person=None)
        sections = sections.filter(person_name__gte=lower_bound).filter(person_name__lt=upper_bound)
        sections_count = sections.count()
        self.logger.info("Start reading {} sections from DB... ".format(sections_count))
        cnt = 0
        for s in sections.all():
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
        persons = Person.objects.filter(section__person_name__gte=lower_bound).filter(section__person_name__lt=upper_bound).distinct()
        persons_count = persons.count()
        self.logger.info("Start reading {} people records from DB...".format(persons_count))
        cnt = 0
        for p in persons.all():
            k, v = TPersonFields(p).get_dedupe_id_and_object()
            if k is None:
                continue
                # no sections for this person, ignore this person
            self.dedupe_objects[k] = v
            cnt += 1
            if cnt % 1000 == 0:
                self.logger.info("Read {} records from person table".format(cnt))
        self.logger.info("Read {} records from person table".format(cnt))

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

        dump_file_name = self.options["dump_dedupe_objects_file"]
        if dump_file_name:
            with open(dump_file_name, "w", encoding="utf-8") as of:
                for k, v in self.dedupe_objects.items():
                    json_value = dedupe_object_writer(v)
                    of.write("\t".join((k, json_value)) + "\n")

    def write_results_to_file(self, clustered_dupes, dump_stream):
        self.logger.info('{} clusters generated'.format(len(clustered_dupes)))
        for id1, id2, score1, score2 in get_pairs_from_clusters(clustered_dupes):
            dump_stream.write("\t".join((id1, id2, str(score1), str(score2))) + "\n")

    def link_section_to_person(self, section, person_id, dedupe_score):
        section.person_id = person_id
        section.dedupe_score = dedupe_score
        section.save()

    def link_sections_to_a_new_person(self, section_ids):
        person = Person()
        person.save()
        for id in section_ids:
            section = Section.objects.get(id=id)
            # dedupe_score is unknown but it must be > 0 for dedupe linked (person, section) pairs
            self.link_section_to_person(section, person.id, 0.9)

    def write_results_to_db(self, clustered_dupes):
        self.logger.info('write {} results to db'.format(len(clustered_dupes)))
        linked_sections = set()
        if clustered_dupes != None:
            self.logger.info('Write back to DB'.format(len(clustered_dupes)))
            for id1, id2, score1, score2 in get_pairs_from_clusters(clustered_dupes):
                if id1.startswith("person-") and id2.startswith("section-"):
                    person_id = int(id1[len("person-"):])
                    section_id = int(id2[len("section-"):])
                    section = Section.objects.get(id=section_id)
                    self.link_section_to_person(section, person_id, float(score2))
                    linked_sections.add(section_id)

        self.logger.info('Create new people by dedupe clusters... ')
        if clustered_dupes is not None:
            for (cluster_id, cluster) in enumerate(clustered_dupes):
                new_sections = set()
                id_set, scores = cluster
                has_person_in_cluster = False
                for id, score in zip(id_set, scores):
                    if id.startswith("section-"):
                        section_id = int(id[len("section-"):])
                        if section_id not in linked_sections:
                            new_sections.add(section_id)
                    if id.startswith("person-"):
                        has_person_in_cluster = True
                if len(new_sections) != 0:
                    if has_person_in_cluster:
                        self.logger.info('ignore a strange cluster with section ids = {0} ... '.format(new_sections))
                    else:
                        self.link_sections_to_a_new_person(new_sections)
                        linked_sections.update(new_sections)

    def get_family_name_bounds(self):
        if self.options.get('surname_bounds') is not None:
            yield self.options.get('surname_bounds').split(',')
        elif self.options.get("input_dedupe_objects") is not None:
            yield None, None
        else:
            all_borders = '0,А,Б,БП,В,Г,ГП,Д,Е,Ж,З,И,К,КН,Л,М,МН,Н,О,П,ПН,Р,С,СН,Т,У,Ф,Х,Ц,Ч,Ш,Щ,Э,Ю,Я,♪'.split(',')
            for x in range(1, len(all_borders)):
                yield all_borders[x-1], all_borders[x]

    def handle(self, *args, **options):

        self.logger.info('Started at: {}'.format(datetime.now()))
        self.init_options(options)
        if options.get('print_family_prefixes'):
            for lower_bound, upper_bound in self.get_family_name_bounds():
                sys.stdout.write("{},{}\n".format(lower_bound, upper_bound))
            return
        stop_elastic_indexing()

        with open(options["model_file"], 'rb') as sf:
            self.logger.info('read dedupe settings from {}'.format(sf.name))
            self.dedupe = dedupe.StaticDedupe(sf, num_cores=options['num_cores'])
            if logging.getLogger().getEffectiveLevel() > 1:
                describe_dedupe(self.stdout, self.dedupe)

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
            clustered_dupes = None

            try:
                self.logger.debug(
                    'Clustering {} objects with threshold={}.'.format(len(self.dedupe_objects), threshold))
                clustered_dupes = self.dedupe.match(self.dedupe_objects, threshold)
            except Exception as e:
                self.logger.error(
                    'Dedupe failed for this cluster, possibly no blocks found, ignore result: {0}'.format(e))

            if clustered_dupes is not None:
                if dump_stream is not None:
                    self.write_results_to_file(clustered_dupes, dump_stream)
            if options['write_to_db']:
                self.write_results_to_db(clustered_dupes)

        if dump_stream is not None:
            dump_stream.close()

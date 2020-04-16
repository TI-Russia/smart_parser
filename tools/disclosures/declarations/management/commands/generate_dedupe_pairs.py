# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import dedupe
import logging
from datetime import datetime
from django.core.management import BaseCommand, CommandError
from declarations.models import Person, Section
from .dedupe_adapter import TPersonFields, dedupe_object_reader, dedupe_object_writer, describe_dedupe, \
    get_pairs_from_clusters
from deduplicate.config import resolve_fullname


class Command(BaseCommand):
    help = ''

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            dest='verbose',
            type=int,
            help='Increase verbosity',
            default=0
        )
        parser.add_argument(
            '--family-prefix',
            dest='family_prefix',
            default='',
            help='Russian uppercase char',
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
        self.family_prefix = None
        self.dedupe_objects = None
        self.options = None

    def init_options(self, options):
        self.options = options
        self.family_prefix = options['family_prefix'].upper()
        log_level = logging.WARNING
        if options.get("verbose"):
            if options.get("verbose") == 1:
                log_level = logging.INFO
            elif options.get("verbose") >= 2:
                log_level = logging.DEBUG
        logging.getLogger().setLevel(log_level)

    def fill_dedupe_data(self):
        self.dedupe_objects = {}

        input_dump_file = self.options.get("input_dedupe_objects")
        if input_dump_file is not None:
            with open(input_dump_file, "r", encoding="utf-8") as fp:
                for line in fp:
                    (k, v) = line.strip().split("\t")
                    self.dedupe_objects[str(k)] = dedupe_object_reader(v)
            return

        sections = Section.objects.filter(person=None).filter(person_name__istartswith=self.family_prefix)
        self.stdout.write("Read sections from DB family_prefix={}...".format(self.family_prefix))
        cnt = 0
        for s in sections.all():
            k, v = TPersonFields(None, s).get_dedupe_id_and_object()
            assert (k != None)
            if len(v['family_name']) == 0:
                continue # ignore sections with broken person names, because dedupe fails
            self.dedupe_objects[k] = v
            cnt += 1
        self.stdout.write("Read {0} from section table".format(cnt))

        persons = Person.objects.filter(section__person_name__istartswith=self.family_prefix).distinct().all()
        self.stdout.write("Read people from DB family_prefix={}...".format(self.family_prefix))
        cnt = 0
        for p in persons:
            k, v = TPersonFields(p).get_dedupe_id_and_object()
            if k == None:
                continue
                # no sections for this person, ignore this person
            self.dedupe_objects[k] = v
            cnt += 1
        self.stdout.write("Read {0} from person table".format(cnt))

        self.stdout.write("All objects  for dedupe = {} ".format(len(self.dedupe_objects)))

        dump_file_name = self.options["dump_dedupe_objects_file"]
        if dump_file_name:
            with open(dump_file_name, "w", encoding="utf-8") as of:
                for k, v in self.dedupe_objects.items():
                    json_value = dedupe_object_writer(v)
                    of.write("\t".join((k, json_value)) + "\n")

    def write_results_to_file(self, clustered_dupes, dump_stream):
        self.stdout.write('{} clusters generated'.format(len(clustered_dupes)))
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
        linked_sections = set()
        if clustered_dupes != None:
            self.stdout.write('Write back to DB'.format(len(clustered_dupes)))
            for id1, id2, score1, score2 in get_pairs_from_clusters(clustered_dupes):
                if id1.startswith("person-") and id2.startswith("section-"):
                    person_id = int(id1[len("person-"):])
                    section_id = int(id2[len("section-"):])
                    section = Section.objects.get(id=section_id)
                    self.link_section_to_person(section, person_id, float(score2))
                    linked_sections.add(section_id)

        self.stdout.write('Create new people by dedupe clusters... ')
        if clustered_dupes != None:
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
                        self.stdout.write('ignore a strange cluster with section ids = {0} ... '.format(new_sections))
                    else:
                        self.link_sections_to_a_new_person(new_sections)
                        linked_sections.update(new_sections)


    def handle(self, *args, **options):

        self.stdout.write('Started at: {}'.format(datetime.now()))
        self.init_options(options)

        with open(options["model_file"], 'rb') as sf:
            self.stdout.write('read dedupe settings from {}'.format(sf.name))
            self.dedupe = dedupe.StaticDedupe(sf, num_cores=options['num_cores'])
            if logging.getLogger().getEffectiveLevel() > 1:
                describe_dedupe(self.stdout, self.dedupe)

        threshold = 0
        if options.get('threshold', 0) != 0:
            threshold = options.get('threshold')
        else:
            self.stdout.write('Warning! Threshold is not set. Is it just a test?')

        if len(self.family_prefix) == 0:
            if self.options.get("input_dedupe_objects") is None:
                all_prefixes = list("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
            else:
                all_prefixes = ["dummy"]
        else:
            all_prefixes = [self.family_prefix]

        dump_stream = None
        dump_file_name = self.options.get("result_pairs_file")
        if dump_file_name:
            dump_stream = open(dump_file_name, "w", encoding="utf8")
            if options.get("verbose", 0) > 0:
                self.stdout.write(u'write result pairs to {}\n'.format(dump_file_name))

        if options.get("verbose", 0) > 0:
            self.stdout.write(u"go through prefixes {}".format(",".join(all_prefixes)))

        for x in range(len(all_prefixes)):

            self.family_prefix = all_prefixes[x]
            if options.get("verbose", 0) > 0:
                self.stdout.write("prefix {0}".format(self.family_prefix))
            self.fill_dedupe_data()
            clustered_dupes = None

            try:
                if options.get("verbose", 0) > 0:
                    self.stdout.write(
                        u'Clustering {} objects with threshold={}.'.format(len(self.dedupe_objects), threshold))
                clustered_dupes = self.dedupe.match(self.dedupe_objects, threshold)
            except Exception as e:
                self.stdout.write(
                    u'Dedupe failed for this cluster, possibly no blocks found, ignore result: {0}'.format(e))

            if clustered_dupes is not None:
                if dump_stream is not None:
                    self.write_results_to_file(clustered_dupes, dump_stream)
            if options['write_to_db']:
                self.write_results_to_db(clustered_dupes)

        if dump_stream is not None:
            dump_stream.close()

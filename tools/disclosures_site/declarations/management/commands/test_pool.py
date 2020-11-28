# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import dedupe
import logging
import json
import os
from datetime import datetime

from django.core.management import BaseCommand

from collections import Counter
from deduplicate.toloka import TToloka
from .dedupe_adapter import \
    dedupe_object_writer, \
    describe_dedupe, \
    get_pairs_from_clusters, \
    pool_to_dedupe

# more info on 70..100 to get more accuracy
ROC_POINTS = list(range(0, 71, 10)) + list(range(71, 100))




def setup_logging(logfilename="test_pool.log"):
    logger = logging.getLogger("toloka")
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

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


class Command(BaseCommand):
    help = 'Test dedupe model file, build report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            dest='verbose',
            type=int,
            help='Increase verbosity',
            default=0
        )
        parser.add_argument(
            '--test-pool',
            dest='test_pool',
            default=[],
            action="append",
            help='test pool in toloka tsv format, possible many times',
        )
        parser.add_argument(
            '--test-only-human-rules',
            dest='test_only_human_rules',
            default=False,
            action="store_true",
        )
        parser.add_argument(
            '--dedupe-model-file',
            dest='model_file',
            default="dedupe.info",
            help='dedupe settings (trained model)',
        )
        parser.add_argument(
            '--threshold',
            dest='threshold',
            default=None,
            type=float,
            help='a custom threshold',
        )
        parser.add_argument(
            '--dump-dedupe-objects-file',
            dest='dump_dedupe_objects_file',
            help='',
        )
        parser.add_argument(
            '--test-output',
            dest='test_output',
            default=None
        )
        parser.add_argument(
            '--test-output-fields',
            dest='test_output_fields',
            default=False,
            action="store_true",
            help="store to test-output all fields"
        )
        parser.add_argument(
            '--points-file',
            dest='points_file',
            default="points.txt",
            help='output points file',
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.test_data = None
        self.options = None
        self.dedupe_objects = {}
        self.match = []
        self.distinct = []
        self.logger = setup_logging()

    def init_options(self, options):
        self.options = options
        log_level = logging.WARNING
        if options.get("verbose"):
            if options.get("verbose") == 1:
                log_level = logging.INFO
            elif options.get("verbose") >= 2:
                log_level = logging.DEBUG

        logging.getLogger().setLevel(log_level)

    def fill_dedupe_data(self):
        self.dedupe_objects = {}
        self.match = []
        self.distinct = []
        pool_to_dedupe(self.logger, self.test_data, self.dedupe_objects, self.match, self.distinct)

        self.log("Read {} objects from the input pool".format(len(self.dedupe_objects)))

        dump_file_name = self.options["dump_dedupe_objects_file"]
        if dump_file_name:
            with open(dump_file_name, "w", encoding="utf-8") as of:
                for k, v in self.dedupe_objects.items():
                    json_value = dedupe_object_writer(v)
                    of.write("\t".join((k, json_value)) + "\n")

    def log(self, m):
        self.logger.debug(m)

    def process_test_with_threshold(self, point):
        with open(self.options["model_file"], 'rb') as sf:
            dedupe_model = dedupe.StaticDedupe(sf, num_cores=1)
            clustered_dupes = dedupe_model.match(self.dedupe_objects, point['Threshold'])
            pairs = get_pairs_from_clusters(self.logger, clustered_dupes)
            (metrics, results) = TToloka.calc_metrics(pairs, self.test_data)
            point.update(metrics)
            return point, results, clustered_dupes

    def print_test_output(self, test_results):
        if self.options.get("test_output") is not None:
            with open(self.options.get("test_output"), "w", encoding="utf-8") as f:
                self.log("store test results to {}\n".format(f.name))
                for s in test_results:
                    if self.options['test_output_fields']:
                        f1 = dedupe_object_writer(self.dedupe_objects[s[0]])
                        f2 = dedupe_object_writer(self.dedupe_objects[s[1]])
                        s = list(s) + [f1, f2]
                    line = "\t".join(s) + "\n"
                    f.write(line)

    def print_roc_points(self, test_pool_file_name, output_points_file):
        points = []
        for t in ROC_POINTS:
            points.append ({'Threshold': t / 100.0})

        for p in points:
            p['TestName'] = os.path.basename(test_pool_file_name)

        for metrics, _, _ in map(self.process_test_with_threshold, points):
            output_points_file.write(json.dumps(metrics) + "\n")

    # ignore reweighting inside clusters, use print_roc_points_quick_and_dirty for larger models
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.distance.squareform.html
    def print_roc_points_quick_and_dirty(self, test_pool_file_name, output_points_file):
        with open(self.options["model_file"], 'rb') as sf:
            dedupe_model = dedupe.StaticDedupe(sf)
            clustered_dupes = dedupe_model.match(self.dedupe_objects, 0)
        for t in ROC_POINTS:
            threshold = t / 100.0
            pairs = get_pairs_from_clusters(self.logger, clustered_dupes, threshold=threshold)
            (metrics, test_results) = TToloka.calc_metrics(pairs, self.test_data)
            self.print_test_output(test_results)

            metrics['Threshold'] = threshold
            metrics['TestName'] = os.path.basename(test_pool_file_name)
            output_points_file.write(json.dumps(metrics) + "\n")

    def process_test(self, test_pool_file_name, output_points_file):
        self.test_data = TToloka.read_toloka_golden_pool(test_pool_file_name)
        self.log(
            "Mark distribution in {}: {}".format(self.options["test_pool"], repr(Counter(self.test_data.values()))))
        self.fill_dedupe_data()
        if self.options.get('threshold') is not None:
            threshold = self.options.get('threshold')
            metrics, test_results, dupes = self.process_test_with_threshold({'Threshold': threshold, 'self': self})
            self.print_test_output(test_results)
            metrics.pop('self')
            self.logger.info(json.dumps(metrics) + "\n")
        else:
            self.print_roc_points(test_pool_file_name, output_points_file)
            #self.print_roc_points_quick_and_dirty(test_pool_file_name, output_points_file)


    def handle(self, *args, **options):

        self.init_options(options)
        self.log('Started at: {}'.format(datetime.now()))

        if self.options.get("verbose") > 0:
            with open(self.options["model_file"], 'rb') as sf:
                describe_dedupe(self.logger, dedupe.StaticDedupe(sf))

        with open(self.options["points_file"], 'w', encoding="utf8") as outf:
            for test_pool in options["test_pool"]:
                if options['test_only_human_rules']:
                    self.apply_auto_negative_rules()
                else:
                    self.process_test(test_pool, outf)


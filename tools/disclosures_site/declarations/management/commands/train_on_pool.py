# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import dedupe
from django.core.management import BaseCommand

from .dedupe_adapter import dedupe_object_writer, describe_dedupe, pool_to_dedupe
from deduplicate.toloka import TToloka

from sklearn.ensemble import RandomForestClassifier
import json
import logging
from datetime import datetime


class Command(BaseCommand):
    help = 'Обучение модели Dedupe на основе train+test пула'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loglevel',
            dest='loglevel',
            help='DEBUG, INFO or ERROR',
            default='ERROR'
        )
        parser.add_argument(
            '--logfile',
            dest='logfile',
            default=None
        )
        parser.add_argument(
            '--train-pool',
            dest='train_pool',
            default=None,
        )
        parser.add_argument(
            '--ml-model-file',
            dest='model_file',
            default="dedupe.info",
            help='dedupe settings (trained model)',
        )
        parser.add_argument(
            '--use-random-forest',
            dest='use_random_forest',
            default=False,
            action="store_true",
            help='use random forest to rank hypots',
        )
        parser.add_argument(
            '--train-options',
            dest='train_options',
            default="train.options",
            help='a file to write the train options',
        )
        parser.add_argument(
            '--dump-train-objects-file',
            dest='dump_train_objects_file',
            help='a file to write all train objects',
        )
        parser.add_argument(
            '--dedupe-train-recall',
            dest='dedupe_train_recall',
            default=0.95,
            type=float,
            help='dedupe.train (recall=)',
        )
        parser.add_argument(
            '--output-training-pairs-file',
            dest='output_training_pairs_file',
            help='write training in dedupe format',
        )
        parser.add_argument(
            '--add-train-pool',
            dest='additional_train_pool',
            default=None,
            help='additional_train',
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.dedupe = None
        self.train_pool = None
        self.train_objects = None
        self.train_pairs = None
        self.dedupe_train_recall = 0.95
        self.threshold = None
        self.options = None

    def init_options(self, options):
        self.dedupe_train_recall = options['dedupe_train_recall']
        self.options = options

        logger = logging.getLogger('dedupe_declarator_logger')
        loglevel = options['loglevel'].upper()
        numeric_level = getattr(logging, loglevel, None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)
        logger.setLevel(numeric_level)
        logging.debug("set log level to {0}".format(loglevel))
        if options['logfile'] is not None:
            fh = logging.FileHandler(options['logfile'])
            logger.addHandler(fh)

    def build_train_objects_and_pairs(self):
        self.train_objects = {}
        match = []
        distinct = []
        pool_to_dedupe(self.train_pool, self.train_objects, match, distinct)

        if self.options['additional_train_pool'] is not None:
            add_train_pool = TToloka.read_toloka_golden_pool(self.options["additional_train_pool"])
            pool_to_dedupe(add_train_pool, self.train_objects, match, distinct)

        self.stdout.write("Total data records loaded: {}".format(len(self.train_objects)))
        self.stdout.write("Match pairs: {}".format(len(match)))
        self.stdout.write("Distinct pairs: {}".format(len(distinct)))

        self.train_pairs = {
            'match': match,
            'distinct': distinct
        }

        if self.options.get("dump_train_objects_file"):
            with open(self.options.get("dump_train_objects_file"), "w", encoding="utf-8") as of:
                for k, v in self.train_objects.items():
                    json_value = dedupe_object_writer(v)
                    of.write("\t".join((k, json_value)) + "\n")

    def write_dedupe_aux_params(self):
        with open(self.options["train_options"], 'w', encoding="utf8") as sf:
            self.stdout.write('write dedupe threshold to {}'.format(sf.name))
            params = {
                "threshold": self.threshold,
                "options": self.options
            }

            json.dump(params, sf, ensure_ascii=False)

    def handle(self, *args, **options):
        self.stdout.write('Started at: {}'.format(datetime.now()))
        self.init_options(options)
        self.train_pool = TToloka.read_toloka_golden_pool(options["train_pool"])

        from deduplicate.config import fields
        self.dedupe = dedupe.Dedupe(fields, num_cores=2)
        if self.options['use_random_forest']:
            self.dedupe.classifier = RandomForestClassifier(n_estimators=300, max_depth=4, random_state=0)

        self.build_train_objects_and_pairs()

        self.stdout.write("Start of sampling...")
        self.dedupe.sample(self.train_objects)

        self.stdout.write("run dedupe markPairs distint count={} match count={}".format(
            len(self.train_pairs['distinct']), len(self.train_pairs['match']))
        )
        self.dedupe.markPairs(self.train_pairs)

        self.stdout.write('Training...')
        self.dedupe.train(recall=self.dedupe_train_recall, index_predicates=False)

        self.threshold = float(self.dedupe.threshold(self.train_objects))
        self.stdout.write('Selected threshold = {}'.format(self.threshold))
        with open(options["model_file"], 'wb') as sf:
            self.stdout.write('write dedupe settings to {}'.format(sf.name))
            self.dedupe.writeSettings(sf, index=False)

        if self.options['output_training_pairs_file']:
            with open(self.options.get("output_training_pairs_file"), "w", encoding="utf-8") as tf:
                self.dedupe.writeTraining(tf)

        self.write_dedupe_aux_params()
        describe_dedupe(self.stdout, self.dedupe)

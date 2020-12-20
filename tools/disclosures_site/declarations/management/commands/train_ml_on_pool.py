from .random_forest_adapter import pool_to_random_forest, TDeduplicationObject
from deduplicate.toloka import TToloka

from django.core.management import BaseCommand
from sklearn.ensemble import RandomForestClassifier
import json
import logging
import os
import pickle


def setup_logging(logfilename="train_ml_pool.log"):
    logger = logging.getLogger("train_ml_pool")
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
    help = 'Обучение модели Dedupe на основе train+test пула'

    def add_arguments(self, parser):
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
            default="random_forest.pickle",
            help='random forest trained model',
        )
        parser.add_argument(
            '--dump-train-objects-file',
            dest='dump_train_objects_file',
            help='a file to write all train objects',
        )
        parser.add_argument(
            '--output-training-pairs-file',
            dest='output_training_pairs_file',
            help='write training in dedupe format',
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.ml_model = None
        self.train_pool = None
        self.train_objects = None
        self.X = None
        self.y_true = None
        self.threshold = None
        self.options = None
        self.logger = setup_logging()

    def build_train_objects_and_pairs(self):
        self.train_objects, self.X, self.y_true = pool_to_random_forest(self.logger, self.train_pool)
        self.logger.info("Match pairs: {}".format(sum(1 for i in self.y_true if i == 1)))
        self.logger.info("Distinct pairs: {}".format(sum(1 for i in self.y_true if i == 0)))

        if self.options.get("dump_train_objects_file"):
            with open(self.options.get("dump_train_objects_file"), "w") as of:
                for o in self.train_objects:
                    of.write(json.dumps(o.to_json(), indent=4, ensure_ascii=False))

    def print_feature_importance(self):
        self.logger.info("feature importance:")
        for name, weight in zip(TDeduplicationObject.get_feature_names(), self.ml_model.feature_importances_):
            self.logger.info("\t{} {}".format(name, weight))

    def handle(self, *args, **options):
        self.options = options
        self.logger.info('read {}'.format(self.options["train_pool"]))
        self.train_pool = TToloka.read_toloka_golden_pool(self.options["train_pool"])
        self.ml_model = RandomForestClassifier(n_estimators=300, max_depth=4, random_state=0)
        self.build_train_objects_and_pairs()
        self.logger.info("Start learning...")
        self.ml_model.fit(self.X, self.y_true)
        self.print_feature_importance()
        with open(options["model_file"], 'wb') as sf:
            self.logger.info('write ml model to {}'.format(sf.name))
            sf.write(pickle.dumps(self.ml_model))
        self.logger.info("all done")


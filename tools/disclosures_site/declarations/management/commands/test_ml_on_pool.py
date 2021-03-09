from .random_forest_adapter import pool_to_random_forest, TMLModel
from deduplicate.toloka import TToloka
from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand
import json
import os
from sklearn.metrics import precision_recall_curve


class Command(BaseCommand):
    help = 'Test random forest model file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-pool',
            dest='test_pool',
            help='test pool in toloka tsv format',
        )
        parser.add_argument(
            '--ml-model-file',
            dest='model_file',
            required=True
        )
        parser.add_argument(
            '--desired-precision',
            dest='desired_precision',
            default=0.99,
            type=float,
        )
        parser.add_argument(
            '--points-file',
            dest='points_file',
            default="points.txt",
            help='output points file',
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.test_objects = None
        self.test_data = None
        self.options = None
        self.logger = setup_logging(log_file_name="test_ml_pool.log")
        self.ml_model = None
        self.X = None
        self.y_true = None

    def print_roc_points(self, test_pool_file_name, output_points_file):
        y_proba = self.ml_model.predict_positive_proba(self.X)
        precision, recall, thresholds = precision_recall_curve(self.y_true, y_proba)
        for precision, recall, threshold in zip(precision, recall, thresholds):
            point = {'Threshold': float(threshold),
                     'TestName': os.path.basename(test_pool_file_name),
                     'P': float(precision),
                     'R': float(recall)
                     }
            point_str = json.dumps(point)
            #if abs(precision - self.options['desired_precision']) < 0.005:
            #    self.logger.info(point_str)
            output_points_file.write(point_str + "\n")

    def handle(self, *args, **options):
        self.options = options
        self.ml_model = TMLModel(self.options["model_file"])

        self.logger.info("read {}".format(options["test_pool"]))
        self.test_data = TToloka.read_toloka_golden_pool(options["test_pool"])
        self.test_objects, self.X, self.y_true = pool_to_random_forest(self.logger, self.test_data)
        self.logger.info("Match pairs: {}".format(sum(1 for i in self.y_true if i == 1)))
        self.logger.info("Distinct pairs: {}".format(sum(1 for i in self.y_true if i == 0)))

        with open(self.options["points_file"], 'w', encoding="utf8") as outf:
            self.print_roc_points(options["test_pool"], outf)


from .random_forest_adapter import check_pool_after_real_clustering
from deduplicate.toloka import TToloka

from django.core.management import BaseCommand
import logging
import os
from sklearn.metrics import precision_score, recall_score


def setup_logging(logfilename="test_real_clustering.log"):
    logger = logging.getLogger("test_real_clustering")
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

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-pool',
            dest='test_pool',
            help='test pool in toloka tsv format',
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None
        self.logger = setup_logging()

    def handle(self, *args, **options):
        self.options = options
        self.logger.info("read {}".format(options["test_pool"]))
        test_data = TToloka.read_toloka_golden_pool(options["test_pool"])
        y_true, y = check_pool_after_real_clustering(self.logger, test_data)
        self.logger.info("Match pairs: {}".format(sum(1 for i in y_true if i == 1)))
        self.logger.info("Distinct pairs: {}".format(sum(1 for i in y_true if i == 0)))
        self.logger.info("Precision : {}".format(precision_score(y_true, y)))
        self.logger.info("Recall : {}".format(recall_score(y_true, y)))


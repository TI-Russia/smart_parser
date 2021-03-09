from .random_forest_adapter import check_pool_after_real_clustering
from deduplicate.toloka import TToloka
from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand


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
        self.logger = setup_logging(log_file_name="test_real_clustering.log")

    def handle(self, *args, **options):
        self.options = options
        self.logger.info("read {}".format(options["test_pool"]))
        test_data = TToloka.read_toloka_golden_pool(options["test_pool"])
        cases = check_pool_after_real_clustering(self.logger, test_data)
        self.logger.info("Match pairs: {}".format(cases.match_pairs_count()))
        self.logger.info("Distinct pairs: {}".format(cases.distinct_pairs_count()))
        precision = cases.get_precision()
        recall = cases.get_recall()
        self.logger.info("Precision : {}".format(precision))
        self.logger.info("Recall : {}".format(recall))
        for t  in cases.test_cases:
            self.logger.debug("{} {} {} {} {} {}".format(t.id1, t.id2, t.person_name1, t.person_name2, t.y_true, t.y_pred, ))
        assert precision > 0.95
        assert recall > 0.95
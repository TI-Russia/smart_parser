from disclosures_site.predict_office.office_pool import TOfficePool
from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand
import random

class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument("--declarator-pool", dest='declarator_pool', required=True)
        parser.add_argument("--real-pool", dest='real_pool', required=False)
        parser.add_argument("--real-pool-add-count", dest='real_pool_add_count', required=False, type=int, default=6)
        parser.add_argument("--train-pool", dest='train_pool')
        parser.add_argument("--test-pool", dest='test_pool', required=False)
        parser.add_argument("--test-ratio", dest='test_ratio', required=False, type=float, default=0.2)
        parser.add_argument("--row-count", dest='row_count', required=False, type=int)

    def handle(self, *args, **options):
        logger = setup_logging(log_file_name="split_train.log")
        logger.info("read declarator pool {}".format(options['declarator_pool']))
        pool = TOfficePool(logger)
        pool.read_cases(options['declarator_pool'], row_count=options['row_count'], make_uniq=True)

        if 'real_pool' in options and options['real_pool'] is not None:
            logger.info("read {} and add {} times to declarator pool".format(
                options['real_pool'], options['real_pool_add_count']))
            real_pool = TOfficePool(logger)
            real_pool.read_cases(options['real_pool'])
            for i in range (options['real_pool_add_count']):
                pool.pool.extend(real_pool.pool)
            random.shuffle(pool.pool)
        pool.split(options['train_pool'], options['test_pool'], test_size=options['test_ratio'])

from disclosures_site.declarations.statistics import TDisclosuresStatisticsHistory
from common.logging_wrapper import setup_logging
from django.core.management import BaseCommand


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument("--crawl-epoch", dest='crawl_epoch', type=int, required=True)
        parser.add_argument("--check-metric", dest='check_metric', required=False)
        parser.add_argument("--skip-checking", dest='skip_checking', required=False, action="store_true", default=False)

    def handle(self, *args, **options):
        crawl_epoch = options['crawl_epoch']
        logger = setup_logging(log_file_name="disclosures_statistics.log")
        history = TDisclosuresStatisticsHistory(logger)
        stats = history.build_current_statistics(crawl_epoch)
        if options.get('check_metric') is not None:
            history.check_sum_metric_increase(stats, [options.get('check_metric')])
        else:
            if not options['skip_checking']:
                history.check_statistics(stats)
            history.add_statistics(stats)
            logger.info("do not forget to commit {}\n".format(history.file_path))
            history.write_to_disk()
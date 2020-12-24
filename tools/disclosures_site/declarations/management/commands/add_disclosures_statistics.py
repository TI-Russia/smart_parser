from django.core.management import BaseCommand
from disclosures_site.declarations.statistics import TDisclosuresStatisticsHistory
import sys


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument("--crawl-epoch", dest='crawl_epoch', type=int, required=True)
        parser.add_argument("--check-metric", dest='check_metric', required=False)

    def handle(self, *args, **options):
        crawl_epoch = options['crawl_epoch']
        history = TDisclosuresStatisticsHistory()
        stats = TDisclosuresStatisticsHistory.build_current_statistics(crawl_epoch)
        if options.get('check_metric') is not None:
            history.check_sum_metric_increase(stats, [options.get('check_metric')])
        else:
            self.check_statistics(stats)
            history.add_statistics(stats)
            sys.stderr.write("do not forget to commit {}\n".format(history.file_path))
            history.write_to_disk()
from django.core.management import BaseCommand
from disclosures_site.declarations.statistics import TDisclosuresStatisticsHistory


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument("--crawl-epoch", dest='crawl_epoch', type=int, required=True)

    def handle(self, *args, **options):
        crawl_epoch = options['crawl_epoch']
        history = TDisclosuresStatisticsHistory()
        history.add_current_statistics(crawl_epoch)
        sys.stderr.write("do not forget to commit {}\n".format(history.file_path))
        history.write_to_disk()
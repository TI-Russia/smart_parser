from disclosures_site.predict_office.office_index import TOfficePredictIndex
from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")

    def handle(self, *args, **options):
        logger = setup_logging(log_file_name="build_office_bigrams.log")
        index = TOfficePredictIndex(logger, options['bigrams_path'])
        index.build()
        index.write()

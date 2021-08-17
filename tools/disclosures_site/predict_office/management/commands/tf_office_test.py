from common.logging_wrapper import setup_logging
from disclosures_site.predict_office.tensor_flow_model import TTensorFlowOfficeModel
import argparse
try:
    from django.core.management import BaseCommand
except Exception as exp:
    from common.django_base_command_monkey import BaseCommand


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
        parser.add_argument("--test-pool", dest='test_pool')
        parser.add_argument("--model-folder", dest='model_folder', required=False)
        parser.add_argument("--threshold", dest='threshold', required=False, type=float, default=[0.6], nargs="*")

    def handle(self, *args, **options):
        logger = setup_logging(log_file_name="predict_office_test.log")
        model = TTensorFlowOfficeModel(logger, options['bigrams_path'], options['model_folder'],
                                       test_pool=options['test_pool'])
        model.test_model(thresholds=options['threshold'])


if __name__ == "__main__":
    command = Command()
    parser = argparse.ArgumentParser()
    command.add_arguments(parser)
    args = parser.parse_args()
    command.handle(None, **args.__dict__)

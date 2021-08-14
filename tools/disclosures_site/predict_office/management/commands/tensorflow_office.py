from common.logging_wrapper import setup_logging
from disclosures_site.predict_office.office_pool import TOfficePool
from disclosures_site.predict_office.tensor_flow_model import TTensorFlowOfficeModel

from django.core.management import BaseCommand


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument("--action", dest='action', required=True, help="can be train, test, toloka, split")
        parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
        parser.add_argument("--all-pool", dest='all_pool')
        parser.add_argument("--train-pool", dest='train_pool')
        parser.add_argument("--test-pool", dest='test_pool')
        parser.add_argument("--model-folder", dest='model_folder', required=False)
        parser.add_argument("--epoch-count", dest='epoch_count', required=False, type=int, default=10)
        parser.add_argument("--row-count", dest='row_count', required=False, type=int)
        parser.add_argument("--dense-layer-size", dest='dense_layer_size', required=False, type=int, default=128)
        parser.add_argument("--toloka-pool", dest='toloka_pool', required=False)
        parser.add_argument("--threshold", dest='threshold', required=False, type=float, default=0.6)

    def handle(self, *args, **options):
        logger = setup_logging(log_file_name="predict_office.log")
        if options['action'] == "split":
            assert options.get('all_pool') is not None
            model = TTensorFlowOfficeModel(logger, options['bigrams_path'], options['model_folder'], options['row_count'])
            TOfficePool(model, options['all_pool']).split(options['train_pool'], options['test_pool'])
        else:
            model = TTensorFlowOfficeModel(logger, options['bigrams_path'], options['model_folder'], options['row_count'],
                                           options['train_pool'], options['test_pool'])
            if options['action'] == "train":
                model.train_tensorflow(options['dense_layer_size'], options['epoch_count'])
            elif options['action'] == "test":
                model.test(options['threshold'])
            elif options['action'] == "toloka":
                model.toloka(options['toloka_pool'])
            else:
                raise Exception("unknown action")


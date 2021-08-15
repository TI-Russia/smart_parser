from common.logging_wrapper import setup_logging
from disclosures_site.predict_office.tensor_flow_model import TTensorFlowOfficeModel

from django.core.management import BaseCommand


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
        parser.add_argument("--train-pool", dest='train_pool')
        parser.add_argument("--model-folder", dest='model_folder', required=False)
        parser.add_argument("--epoch-count", dest='epoch_count', required=False, type=int, default=10)
        parser.add_argument("--row-count", dest='row_count', required=False, type=int)
        parser.add_argument("--dense-layer-size", dest='dense_layer_size', required=False, type=int, default=128)
        parser.add_argument("--batch-size", dest='batch_size', required=False, type=int, default=256)

    def handle(self, *args, **options):
        logger = setup_logging(log_file_name="predict_office_train.log")
        model = TTensorFlowOfficeModel(logger, options['bigrams_path'], options['model_folder'], options['row_count'],
                                       options['train_pool'])
        model.train_tensorflow(options['dense_layer_size'],
                                   epoch_count=options['epoch_count'], batch_size=options['batch_size'])


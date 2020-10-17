import declarations.models as models
from django.core.management import BaseCommand
import logging
import os
import dbm.gnu
import gc   


def setup_logging(logfilename="create_permalink_storage.log"):
    logger = logging.getLogger("copy_primary_keys")
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

    return logger


def queryset_iterator(queryset, chunksize=1000):
    pk = 0
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()


class Command(BaseCommand):
    help = 'create permalink storage (in gnu.dmb format) to make web links almost permanent'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

    def add_arguments(self, parser):
        parser.add_argument(
                '--output-dbm-file',
            dest='output_dbm_file',
            default=None,
            required=True,
            help='write mapping to this fiie'
        )

    def save_permalinks(self, logger, django_db_model, dbm):
        cnt  = 0
        for d in queryset_iterator(django_db_model.objects.all()):
            cnt += 1
            if (cnt % 3000) == 0:
                logger.debug("{}:{}".format(str(django_db_model), cnt))
            dbm[d.permalink_passport()] = str(d.id)

    def handle(self, *args, **options):
        logger = setup_logging()
        db = dbm.gnu.open(options.get('output_dbm_file'), "cs")
        self.save_permalinks(logger, models.Source_Document, db)
        self.save_permalinks(logger, models.Section, db)
        self.save_permalinks(logger, models.Person, db)
        logger.info("all done")

CreatePermalinksStorage=Command

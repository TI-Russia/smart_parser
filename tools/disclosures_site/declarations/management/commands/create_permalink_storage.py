from declarations.management.commands.permalinks import TPermaLinksDB
from common.primitives import queryset_iterator
import declarations.models as models

from django.core.management import BaseCommand
import logging
import os


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


class Command(BaseCommand):
    help = 'create permalink storage (in gnu.dmb format) to make web links almost permanent'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None
        self.logger = None

    def add_arguments(self, parser):
        parser.add_argument(
                '--output-dbm-file',
            dest='output_dbm_file',
            default=None,
            required=True,
            help='write mapping to this fiie'
        )

    def save_dataset(self, db: TPermaLinksDB, model_type, save_function):
        if model_type.objects.count() == 0:
            db.save_max_plus_one_primary_key(model_type, 0)
        else:
            cnt = 0
            max_value = 0
            for record in queryset_iterator(model_type.objects.all()):
                cnt += 1
                if (cnt % 3000) == 0:
                    self.logger.debug("{}".format(cnt))
                save_function(record)
                max_value = max(record.id, max_value)

            db.save_max_plus_one_primary_key(model_type, max_value + 1)

    def handle(self, *args, **options):
        self.logger = setup_logging()

        db = TPermaLinksDB(options.get('output_dbm_file'))
        db.create_db()

        self.save_dataset(db, models.Source_Document, db.save_source_doc)
        db.sync_db()

        self.save_dataset(db, models.Section, db.save_section)
        db.sync_db()

        self.save_dataset(db, models.Person, db.save_person)
        db.close_db()

        self.logger.info("all done")

CreatePermalinksStorageCommand=Command

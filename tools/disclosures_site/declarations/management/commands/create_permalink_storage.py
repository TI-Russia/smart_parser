from declarations.management.commands.permalinks import TPermaLinksDB
from declarations.sql_helpers import queryset_iterator
import declarations.models as models
from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand


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
        self.logger = setup_logging(logger_name="create_permalink_storage")

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

from declarations.management.commands.generate_dedupe_pairs import RunDedupe
import declarations.models as models
from declarations.permalinks import TPermaLinksPerson
from common.logging_wrapper import setup_logging


import os
from django.test import TestCase, tag


class AndreevDedupeTestCase(TestCase):
    @tag('central')
    def test(self):
        logger = setup_logging(logger_name="test_real_dedupe")
        models.Section.objects.all().delete()

        permalinks_folder = os.path.dirname(__file__)

        db = TPermaLinksPerson(permalinks_folder)
        db.open_db_read_only()
        db.recreate_auto_increment_table()
        db.close_db()

        model_path = os.path.join(os.path.dirname(__file__), "../../../deduplicate/model/random_forest.pickle" )
        dedupe_objects = os.path.join(os.path.dirname(__file__), "dedupe_objects.dump")
        run_dedupe = RunDedupe(None, None)
        run_dedupe.handle(None,
                          permalinks_folder=permalinks_folder,
                          input_dedupe_objects=dedupe_objects,
                          model_file=model_path,
                          threshold=0.6,
                          recreate_db=True,
                          surname_bounds=',',
                          write_to_db=True
                          )
        sec = models.Section.objects.get(id=757036)
        self.assertEqual(1406125, sec.person_id)

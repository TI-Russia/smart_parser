from declarations.management.commands.generate_dedupe_pairs import RunDedupe
import declarations.models as models
from declarations.permalinks import TPermaLinksPerson
from common.logging_wrapper import setup_logging
from declarations.sql_helpers import run_sql_script

import os
from django.test import TestCase


class ComplexDedupeTestCase(TestCase):

    def test(self):
        logger = setup_logging(logger_name="test_real_dedupe")
        sql_script = os.path.join( os.path.dirname(__file__), "disclosures.sql.person_id_5295.n")
        run_sql_script(logger, sql_script)

        permalinks_folder = os.path.dirname(__file__)
        db = TPermaLinksPerson(permalinks_folder)
        db.create_db()
        db.save_dataset(setup_logging())
        db.recreate_auto_increment_table()
        db.close_db()

        model_path = os.path.join(os.path.dirname(__file__), "../../../deduplicate/model/random_forest.pickle" )
        run_dedupe = RunDedupe(None, None)
        run_dedupe.handle(None,
                          permalinks_folder=permalinks_folder,
                          write_to_db=True,
                          surname_bounds=',',
                          model_file=model_path,
                          threshold=0.6
                          )

        person_id = 5295
        self.assertEqual(models.Person.objects.count(), 3)
        person = models.Person.objects.get(id=person_id)
        self.assertIsNotNone(person)
        self.assertEqual(5295, person.declarator_person_id)
        canon_sections  =  [
            (451721,	5295,	True),
            (452066,	5295,	True),
            (452420,	5295, True),
            (453686,	5295, False),
            (455039,	5295,	False),
            (1801614,	5296,	True),
            (5105303,	5295,	True),
            (6437989,	5297,	True),
            (6672563,	5297,	True),
            (6674154,	5297,	True),
            (6773981,	5297,	True),
        ]
        sections = []
        for s in models.Section.objects.all():
            sections.append ((s.id, s.person_id, s.dedupe_score is not None))
        self.assertListEqual(canon_sections, sections)
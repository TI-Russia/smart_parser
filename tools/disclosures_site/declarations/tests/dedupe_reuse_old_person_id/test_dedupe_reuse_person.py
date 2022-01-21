from declarations.management.commands.generate_dedupe_pairs import RunDedupe
from declarations.management.commands.random_forest_adapter import TDeduplicationObject
from django.test import TestCase, tag


class TPermalinksMonkey:
    def __init__(self, section2person=None):
        self.section2person = section2person

    def get_person_id_by_section_id(self, section_id):
        if self.section2person is None:
            return None
        else:
            return self.section2person.get(section_id)


class ReuseOldPersonId(TestCase):
    @tag('central')
    def test1(self):
        dedupe = RunDedupe()
        clusters = {1: [
                        (TDeduplicationObject().from_json({"record_id": [1, "s"], "person_name": "a"}), 1)
                        ],
                    2: [
                        (TDeduplicationObject().from_json({"record_id": [2, "s"], "person_name": "b"}), 1)
                    ]
                    }
        dedupe.permalinks_db = TPermalinksMonkey()
        new_to_old_clusters = dedupe.build_cluster_to_old_person_id(clusters)
        self.assertEqual(0, len(new_to_old_clusters))

    @tag('central')
    def test2(self):
        dedupe = RunDedupe()
        clusters = {1: [
                        (TDeduplicationObject().from_json({"record_id": [1, "s"], "person_name": "a"}), 1)
                        ],
                    2: [
                        (TDeduplicationObject().from_json({"record_id": [2, "s"], "person_name": "b"}), 1)
                    ]
                    }
        dedupe.permalinks_db = TPermalinksMonkey({1:99, 2:99})
        new_to_old_clusters = dedupe.build_cluster_to_old_person_id(clusters)
        self.assertEqual(1, len(new_to_old_clusters))
        self.assertEqual(99, new_to_old_clusters[1])

    @tag('central')
    def test3(self):
        dedupe = RunDedupe()
        clusters = {1:
            [
                (TDeduplicationObject().from_json({"record_id": [1, "s"], "person_name": "a"}), 1)
            ],
            2: [
                (TDeduplicationObject().from_json({"record_id": [2, "s"], "person_name": "b"}), 1),
                (TDeduplicationObject().from_json({"record_id": [3, "s"], "person_name": "c"}), 1)
            ]
        }
        dedupe.permalinks_db = TPermalinksMonkey({1: 99, 2: 99, 3:99})
        new_to_old_clusters = dedupe.build_cluster_to_old_person_id(clusters)
        self.assertEqual(1, len(new_to_old_clusters))
        self.assertEqual(99, new_to_old_clusters[2])

    @tag('central')
    def test4(self):
        dedupe = RunDedupe()
        clusters = {
            1: [
                (TDeduplicationObject().from_json({"record_id": [1, "s"], "person_name": "a"}), 1),
                (TDeduplicationObject().from_json({"record_id": [2, "s"], "person_name": "b"}), 1),
                (TDeduplicationObject().from_json({"record_id": [3, "s"], "person_name": "c"}), 1)
            ]
        }
        dedupe.permalinks_db = TPermalinksMonkey({1: 99, 2: 98, 3:98})
        new_to_old_clusters = dedupe.build_cluster_to_old_person_id(clusters)
        self.assertEqual(1, len(new_to_old_clusters))
        self.assertEqual(98, new_to_old_clusters[1])

from declarations.management.commands.random_forest_adapter import TDeduplicationObject, TFioClustering

from django.test import TestCase
from collections import defaultdict


def init_dedupe_object(id, person_name, realty_squares):
    o  = TDeduplicationObject()
    o.id = id
    o.set_person_name(person_name)
    o.realty_squares = realty_squares
    return o


class TTestMLModel:
    def get_ml_score(self, o1, o2):
        if len(o1.realty_squares.intersection(o2.realty_squares)) > 0:
            return 1
        else:
            return 0


class AmbiguousFio(TestCase):

    def test_ambiguous_ivanov(self):
        objs = [init_dedupe_object(1, "Иванов Владимир Николаевич", {25}),
                init_dedupe_object(2, "Иванов Владислав Николаевич", {26}),
                init_dedupe_object(3, "Иванов В. Н.", {26})
                ]
        cluster_by_minimal_fio = defaultdict(list)
        for c in objs:
            cluster_by_minimal_fio[c.fio.build_fio_with_initials()].append(c)
        self.assertEqual(len(cluster_by_minimal_fio), 1)
        for _, leaf_clusters in cluster_by_minimal_fio.items():
            clustering = TFioClustering(leaf_clusters, TTestMLModel())
            clustering.cluster()
            self.assertEqual(len(clustering.clusters), 2)
            for x in clustering.clusters.values():
                if len(x) == 2:
                    self.assertEqual(x[0][0].id, 2)
                    self.assertEqual(x[1][0].id, 3)

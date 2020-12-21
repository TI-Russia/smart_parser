from declarations.management.commands.random_forest_adapter import TDeduplicationObject, TFioClustering
from django.test import TestCase
from collections import defaultdict


def init_dedupe_object(record_id, person_name):
    o = TDeduplicationObject()
    o.record_id = (record_id, TDeduplicationObject.SECTION)
    o.set_person_name(person_name)
    return o


class TTestMLModel:
    def __init__(self, ml_scores):
        self.ml_scores = ml_scores

    def get_features(self, o1, o2):
        if o1.record_id > o2.record_id:
            o1, o2 = o2, o1
        return [o1.record_id[0], o2.record_id[0]]

    def predict_positive_proba(self, X):
        result = list()
        for x in X:
            if x[0] == x[1]:
                w = 1.0
            else:
                if (x[0], x[1]) not in self.ml_scores:
                    w = 0.0
                else:
                    w = self.ml_scores[(x[0], x[1])]
            result.append(w)
        return result


class AmbiguousFio(TestCase):

    def test_ambiguous_ivanov(self):
        objs = [init_dedupe_object(1, "Иванов Владимир Николаевич"),
                init_dedupe_object(2, "Иванов Владислав Николаевич"),
                init_dedupe_object(3, "Иванов В. Н.")
                ]
        ml_model = TTestMLModel({
            (1, 3): 0.8,
            (2, 3): 0.9
        })
        cluster_by_minimal_fio = defaultdict(list)
        for c in objs:
            cluster_by_minimal_fio[c.fio.build_fio_with_initials()].append(c)
        self.assertEqual(len(cluster_by_minimal_fio), 1)
        for _, leaf_clusters in cluster_by_minimal_fio.items():
            clustering = TFioClustering(leaf_clusters, ml_model, 0.89)
            clustering.cluster()
            self.assertEqual(len(clustering.clusters), 2)
            for x in clustering.clusters.values():
                if len(x) == 2:
                    self.assertEqual(x[0][0].record_id[0], 2)
                    self.assertEqual(x[1][0].record_id[0], 3)

    def test_cluster_merge(self):
        objs = [init_dedupe_object(1, "Иванов В. Н."),
                init_dedupe_object(2, "Иванов В. Н."),
                init_dedupe_object(3, "Иванов В. Н."),
                init_dedupe_object(4, "Иванов В. Н.")
                ]
        ml_model = TTestMLModel({
            (1, 2): 0.99,
            (3, 4): 0.99,
            (2, 3): 0.9
        })
        cluster_by_minimal_fio = defaultdict(list)
        for c in objs:
            cluster_by_minimal_fio[c.fio.build_fio_with_initials()].append(c)
        self.assertEqual(len(cluster_by_minimal_fio), 1)
        for _, leaf_clusters in cluster_by_minimal_fio.items():
            clustering = TFioClustering(leaf_clusters, ml_model, 0.89)
            clustering.cluster()
            self.assertEqual(len(clustering.clusters), 1)

import declarations.models as models
import django.core.exceptions
from common.russian_fio import TRussianFio
from common.primitives import normalize_whitespace

import sys
from unidecode import unidecode
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from collections import defaultdict, namedtuple
import pickle
from sklearn.metrics import precision_score, recall_score


def convert_vehicle(name):
    name = unidecode(name)
    name = normalize_whitespace(name)
    name = name.replace(" ", "")
    name = name.replace("-", "")
    name = name.lower()
    return name

def try_to_float(float_str):
    try:
        if float_str is None:
            return 0
        return float(float_str)
    except:
        return 0


def all_realty_squares(section):
    return set(try_to_float(i.square) for i in section.realestate_set.all())


def children_real_estate_squares(section):
    return set(try_to_float(i.square) for i in section.realestate_set.all()
                    if (i.relative == models.Relative.child_code))


def all_vehicles(section):
    return set(convert_vehicle(i.name) for i in section.vehicle_set.all() if i.name)


def all_positions_words(section):
    if section.position is None:
        return set()
    s = normalize_whitespace(section.position).lower()
    return set(s.split(' '))


def average(num):
    return sum(num) / ( len(num) + 0.0000001)


TDeduplicationRecordId = namedtuple('TDeduplicationRecordId', ['id', 'source_table'])


class TDeduplicationObject:
    INCOMPATIBLE_FIO_WEIGHT = 10000
    PERSON = "p"
    SECTION = "s"

    def __init__(self):
        self.record_id = None
        self.person_name = None
        self.fio = None
        self.realty_squares = set()
        self.surname_rank = 100
        self.name_rank = 100
        self.rubrics = set()
        self.offices = set()
        self.children_real_estates_sum = 0
        self.average_income = 0
        self.years = set()
        self.vehicles = set()
        self.official_position_words = set()
        self.regions = set()
        self.db_section_person_id = None

    def set_person_name(self, person_name):
        self.person_name = person_name
        self.fio = TRussianFio(person_name)

    def initialize(self, record_id: TDeduplicationRecordId, person_name, realty_squares, surname_rank, name_rank, rubrics, offices,
                    children_real_estates, average_income, years, vehicles, official_position_words, regions,
                   db_section_person_id=None):
        self.record_id = record_id
        self.set_person_name(person_name)
        self.realty_squares = set(realty_squares)
        self.surname_rank = surname_rank
        self.name_rank = name_rank
        self.rubrics = rubrics
        self.offices = offices
        self.children_real_estates_sum = sum(children_real_estates)
        self.average_income = average_income
        self.years = years
        self.vehicles = vehicles
        self.official_position_words = official_position_words
        self.regions = regions

        self.db_section_person_id = db_section_person_id
        return self

    def initialize_from_section(self, section):
        return self.initialize(
            TDeduplicationRecordId(section.id, self.SECTION),
            section.person_name,
            all_realty_squares(section),
            section.get_surname_rank(),
            section.get_name_rank(),
            set(list([section.rubric_id])),
            set(list([section.office.id])),
            children_real_estate_squares(section),
            section.get_declarant_income_size(),
            set([section.income_year]),
            all_vehicles(section),
            all_positions_words(section),
            set([section.office.region_id]),
            db_section_person_id=section.person_id
        )

    def initialize_from_person(self, person):
        realty_squares = set()
        children_realty_squares = set()
        max_surname_rank = 0
        max_name_rank = 0
        rubrics = set()
        offices = set()
        main_incomes = list()
        years = set()
        vehicles = set()
        position_words = set()
        regions = set()

        for s in person.section_set.all():
            realty_squares |= all_realty_squares(s)
            children_realty_squares |= children_real_estate_squares(s)
            max_surname_rank = max (s.get_surname_rank(), max_surname_rank)
            max_name_rank = max(s.get_name_rank(), max_name_rank)
            rubrics.add(s.rubric_id)
            offices.add(s.office.id)
            main_incomes.append(s.get_declarant_income_size())
            years.add(s.income_year)
            vehicles |= all_vehicles(s)
            position_words |= all_positions_words(s)
            regions.add(s.office.region_id)

        return self.initialize(
                TDeduplicationRecordId(person.id, self.PERSON),
                person.person_name,
                realty_squares,
                max_surname_rank,
                max_name_rank,
                rubrics,
                offices,
                children_realty_squares,
                average(main_incomes),
                years,
                vehicles,
                position_words,
                regions
        )

    def to_json(self):
        s = dict(self.__dict__.items())
        del s['fio']
        for x in s:
            if isinstance(s[x], set):
                s[x] = list(s[x])
        return s

    def from_json(self, js):
        for k in js:
            if k == 'record_id':
                js[k] = TDeduplicationRecordId(js[k][0], js[k][1])
            elif isinstance(js[k], list):
                js[k] = set(js[k])
        self.__dict__ = dict(js.items())
        self.fio = TRussianFio(self.person_name)
        return self

    def build_features(self, other):
        income_now = self.average_income
        income_past = other.average_income
        if average(self.years) > average(other.years):
            income_now, income_past = income_past, income_now

        return [
            len(self.realty_squares.intersection(other.realty_squares)),
            self.surname_rank,
            min(self.name_rank, other.name_rank),
            len(self.rubrics.intersection(other.rubrics)),
            len(self.offices.intersection(other.offices)),
            abs(self.children_real_estates_sum - other.children_real_estates_sum),
            income_past / (income_now + 0.000000001),
            len(self.vehicles.intersection(other.vehicles)),
            len(self.official_position_words.intersection(other.official_position_words)),
            len(self.regions.intersection(other.regions)),
        ]

    @staticmethod
    def get_feature_names():
        return ["realty_intersection",
                "surname_rank",
                "min_name_rank",
                "common_rubrics", # этот фактор уже шумит, может быть его стоит удалить
                "common_offices",
                'children_real_estates_sum',
                'average_income_ratio',
                'vehicles',
                'official_position_words',
                'common_regions'
                ]

    def __hash__(self):
        return hash(self.record_id)

    def initialize_from_prefixed_id(self, prefixed_is_c):
        if prefixed_is_c.startswith("section-"):
            section_id = int(prefixed_is_c[len("section-"):])
            try:
                return self.initialize_from_section(models.Section.objects.get(id=section_id))
            except models.Section.DoesNotExist:
                raise django.core.exceptions.ObjectDoesNotExist
        elif prefixed_is_c.startswith("person-"):
            person_id = int(prefixed_is_c[len("person-"):])
            try:
                return self.initialize_from_person(models.Person.objects.get(id=person_id))
            except models.Person.DoesNotExist:
                raise django.core.exceptions.ObjectDoesNotExist
        else:
            assert False


class TMLModel:
    def __init__(self, filename):
        self.file_name = filename
        with open(filename, 'rb') as sf:
            self.ml_model = pickle.load(sf)

    def get_features(self, o1, o2):
        return o1.build_features(o2)

    def predict_positive_proba(self, X):
        return list(p1 for p0, p1 in self.ml_model.predict_proba(X))


class TFioClustering:

    def __init__(self, logger, leaf_clusters, ml_model, threshold):
        self.logger = logger
        self.leaf_clusters = leaf_clusters
        self.ml_model = ml_model
        self.square_form_distance_matrix = None
        self.object_to_cluster_index = None
        self.clusters = defaultdict(list)
        self.min_distance = 1.0 - threshold

    def get_distance(self, o1, o2, ml_score):
        if o1.record_id == o2.record_id:
            return 0
        if o1.record_id.source_table == TDeduplicationObject.PERSON and o2.record_id.source_table == TDeduplicationObject.PERSON:
            return TDeduplicationObject.INCOMPATIBLE_FIO_WEIGHT
        if not o1.fio.is_compatible_to(o2.fio):
            return TDeduplicationObject.INCOMPATIBLE_FIO_WEIGHT
        else:
            return 1.0 - ml_score

    def cluster(self):
        if len(self.leaf_clusters) == 1:
            self.clusters[0] = [(self.leaf_clusters[0], 0)]
        else:
            self.square_form_distance_matrix = self.build_redundant_distance_matrix()
            condensed_matrix = squareform(self.square_form_distance_matrix)

            self.logger.debug("linkage method=single...")
            linkage_matrix = linkage(condensed_matrix, method="single")

            self.logger.debug("fcluster...")
            self.object_to_cluster_index = fcluster(linkage_matrix, t=self.min_distance, criterion="distance")

            objects_count = len(self.object_to_cluster_index)
            self.logger.debug("set cluster id to {} objects...".format(objects_count))
            for i in range(objects_count):
                distance = self.get_min_distance(i)
                self.clusters[self.object_to_cluster_index[i]].append((self.leaf_clusters[i], distance))

    def build_redundant_distance_matrix(self):
        leaf_clusters_count = len(self.leaf_clusters)
        self.logger.debug("init features for build_redundant_distance_matrix {}x{}...".format(leaf_clusters_count, leaf_clusters_count))
        """ build scipy squareform, single call predict_proba is too slow """
        square_form_distance_matrix = list()
        X = list()
        for i in range(leaf_clusters_count):
            for k in range(leaf_clusters_count):
                i1, i2 = (i, k) if i < k else (k, i)
                X.append(self.ml_model.get_features(self.leaf_clusters[i1], self.leaf_clusters[i2]))
        ml_scores = self.ml_model.predict_positive_proba(X)

        self.logger.debug("calc distance...")
        for i in range(leaf_clusters_count):
            row = list()
            for k in range(leaf_clusters_count):
                ml_score = ml_scores[i * len(self.leaf_clusters) + k]
                distance = self.get_distance(self.leaf_clusters[i], self.leaf_clusters[k], ml_score)
                row.append(distance)
            square_form_distance_matrix.append(row)
        return square_form_distance_matrix

    def get_distances_to_other_cluster_items(self, index):
        distances = list()
        for i in range(len(self.object_to_cluster_index)):
            if self.object_to_cluster_index[i] == self.object_to_cluster_index[index] and i != index:
                distances.append(self.square_form_distance_matrix[i][index])
        return distances

    def get_average_distance(self, index):
        distances = self.get_distances_to_other_cluster_items(index)
        if len(distances) == 0:
            return 0
        else:
            return float(sum(distances)) / len(distances)

    def get_min_distance(self, index):
        distances = self.get_distances_to_other_cluster_items(index)
        if len(distances) == 0:
            return 0
        else:
            return float(min(distances))


def pool_to_random_forest(logger, pairs):
    sys.stdout.flush()
    missing_cnt = 0
    processed_cnt = 0
    X = list()
    y = list()
    single_objects = set()
    for (id1, id2), mark in pairs.items():
        try:
            processed_cnt += 1
            if processed_cnt % 100 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()
            o1 = TDeduplicationObject().initialize_from_prefixed_id(id1)
            single_objects.add(o1)
            o2 = TDeduplicationObject().initialize_from_prefixed_id(id2)
            single_objects.add(o2)

            #random forest is not symmetric
            X.append(o1.build_features(o2))
            X.append(o2.build_features(o1))

            if mark == "YES":
                logger.debug("{} {} -> YES".format(id1, id2))
                y.append(1)
                y.append(1)
            elif mark == "NO":
                logger.debug("{} {} -> NO".format(id1, id2))
                y.append(0)
                y.append(0)
        except django.core.exceptions.ObjectDoesNotExist as e:
            missing_cnt += 1
            logger.debug("skip pair {0} {1}, since one them is not found in DB".format(id1, id2))

    logger.info("convert pool to dedupe: pool size = {0}, missing_count={1}".format(
        processed_cnt, missing_cnt
    ))
    return single_objects, X, y


class TTestCase:
    def __init__(self, id1, id2, person_name1, person_name2, y_true, y_pred):
        self.id1 = id1
        self.id2 = id2
        self.person_name1 = person_name1
        self.person_name2 = person_name2
        self.y_true = y_true
        self.y_pred = y_pred


class TTestCases:
    def __init__(self):
        self.test_cases = list()

    def add_test_case(self, test_case):
        self.test_cases.append(test_case)

    def y_true(self):
        return list(t.y_true for t in self.test_cases)

    def y_pred(self):
        return list(t.y_pred for t in self.test_cases)

    def match_pairs_count(self):
        return sum(1 for i in self.y_pred() if i == 1)

    def distinct_pairs_count(self):
        return sum(1 for i in self.y_pred() if i == 0)

    def get_precision(self):
        return precision_score(self.y_true(), self.y_pred())

    def get_recall(self):
        return recall_score(self.y_true(), self.y_pred())


def check_pool_after_real_clustering(logger, pairs):
    sys.stdout.flush()
    missing_cnt = 0
    processed_cnt = 0
    test_cases = TTestCases()
    for (id1, id2), mark in pairs.items():
        try:
            processed_cnt += 1
            if processed_cnt % 100 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()
            o1 = TDeduplicationObject().initialize_from_prefixed_id(id1)
            o2 = TDeduplicationObject().initialize_from_prefixed_id(id2)
            if not o1.fio.is_compatible_to(o2.fio):
                raise django.core.exceptions.ObjectDoesNotExist()

            y_true = 1 if mark == "YES" else 0

            if o1.record_id.source_table == TDeduplicationObject.SECTION and o2.record_id.source_table == TDeduplicationObject.SECTION:
                y_pred = 1 if (o1.db_section_person_id is not None) and (o1.db_section_person_id == o2.db_section_person_id) else 0
            else:
                if o1.record_id.source_table == TDeduplicationObject.PERSON:
                    o1, o2 = o2, o1
                    id1, id2 = id2, id1
                y_pred = 1 if o1.db_section_person_id == o2.record_id.id else 0
            test_case = TTestCase (id1, id2, o1.person_name, o2.person_name, y_true, y_pred)
            test_cases.add_test_case(test_case)
        except django.core.exceptions.ObjectDoesNotExist as e:
            missing_cnt += 1
            logger.debug("skip pair {0} {1}, since one them is not found in DB".format(id1, id2))

    logger.info("convert pool to dedupe: pool size = {0}, missing_count={1}".format(
        processed_cnt, missing_cnt
    ))
    return test_cases



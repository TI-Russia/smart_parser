import declarations.models as models
import django.core.exceptions
from declarations.russian_fio import TRussianFio
from common.primitives import normalize_whitespace

import sys
from unidecode import unidecode
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from collections import defaultdict
import pickle


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

    def set_person_name(self, person_name):
        self.person_name = person_name
        self.fio = TRussianFio(person_name)

    def initialize(self, record_id, person_name, realty_squares, surname_rank, name_rank, rubrics, offices,
                    children_real_estates, average_income, years, vehicles, official_position_words):
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
        return self

    def initialize_from_section(self, section):
        return self.initialize(
            (section.id, self.SECTION),
            section.person_name,
            all_realty_squares(section),
            section.get_surname_rank(),
            section.get_name_rank(),
            set(list([section.rubric_id])),
            set(list([section.source_document.office.id])),
            children_real_estate_squares(section),
            section.get_declarant_income_size(),
            set([section.income_year]),
            all_vehicles(section),
            all_positions_words(section)
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

        for s in person.section_set.all():
            realty_squares |= all_realty_squares(s)
            children_realty_squares |= children_real_estate_squares(s)
            max_surname_rank = max (s.get_surname_rank(), max_surname_rank)
            max_name_rank = max(s.get_name_rank(), max_name_rank)
            rubrics.add(s.rubric_id)
            offices.add(s.source_document.office.id)
            main_incomes.append(s.get_declarant_income_size())
            years.add(s.income_year)
            vehicles |= all_vehicles(s)
            position_words |= all_positions_words(s)

        return self.initialize(
                (person.id, self.PERSON),
                person.person_name,
                realty_squares,
                max_surname_rank,
                max_name_rank,
                rubrics,
                offices,
                children_realty_squares,
                sum(main_incomes)/len(main_incomes),
                years,
                vehicles,
                position_words
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
            if isinstance(js[k], list):
                js[k] = set(js[k])
        self.__dict__ = dict(js.items())
        self.fio = TRussianFio(self.person_name)
        return self

    def build_features(self, other):
        min_year_diff = min (abs(y1-y2) for y1 in self.years for y2 in other.years)

        return [
            len(self.realty_squares.intersection(other.realty_squares)),
            self.surname_rank,
            min(self.name_rank, other.name_rank),
            len(self.rubrics.intersection(other.rubrics)),
            len(self.offices.intersection(other.offices)),
            abs(self.children_real_estates_sum - other.children_real_estates_sum),
            self.average_income / (other.average_income + 0.000000001),
            min_year_diff,
            len(self.vehicles.intersection(other.vehicles)),
            len(self.official_position_words.intersection(other.official_position_words)),
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
                'years_distance',
                'vehicles',
                'official_position_words'
                ]

    def __hash__(self):
        return hash(self.record_id)

    def initialize_from_prefixed_id(self, prefixed_record_id):
        if prefixed_record_id.startswith("section-"):
            section_id = int(prefixed_record_id[len("section-"):])
            try:
                return self.initialize_from_section(models.Section.objects.get(id=section_id))
            except models.Section.DoesNotExist:
                raise django.core.exceptions.ObjectDoesNotExist
        elif prefixed_record_id.startswith("person-"):
            person_id = int(prefixed_record_id[len("person-"):])
            try:
                return self.initialize_from_person(models.Person.objects.get(id=person_id))
            except models.Person.DoesNotExist:
                raise django.core.exceptions.ObjectDoesNotExist
        else:
            assert False


class TFioClustering:

    def __init__(self, leaf_clusters, ml_model, threshold):
        self.leaf_clusters = leaf_clusters
        self.ml_model = ml_model
        self.square_form_distance_matrix = None
        self.object_to_cluster_index = None
        self.clusters = defaultdict(list)
        self.threshold = 1.0 - threshold

    def get_distance(self, o1, o2):
        if o1.record_id == o2.record_id:
            return 0
        if o1.record_id[1] == TDeduplicationObject.PERSON and o2.record_id[1] == TDeduplicationObject.PERSON:
            return TDeduplicationObject.INCOMPATIBLE_FIO_WEIGHT
        if not o1.fio.is_compatible_to(o2.fio):
            return TDeduplicationObject.INCOMPATIBLE_FIO_WEIGHT
        else:
            return 1.0 - self.ml_model.get_ml_score(o1, o2)

    def cluster(self):
        if len(self.leaf_clusters) == 1:
            self.clusters[0] = [(self.leaf_clusters[0], 0)]
        else:
            self.square_form_distance_matrix = self.build_redundant_distance_matrix()
            condensed_matrix = squareform(self.square_form_distance_matrix)
            linkage_matrix = linkage(condensed_matrix, method="average")
            self.object_to_cluster_index = fcluster(linkage_matrix, t=self.threshold, criterion="distance")
            for i in range(len(self.object_to_cluster_index)):
                #distance = self.get_average_distance(i)
                distance = self.get_min_distance(i)
                self.clusters[self.object_to_cluster_index[i]].append((self.leaf_clusters[i], distance))

    def build_redundant_distance_matrix(self):
        """ build scipy squareform """
        square_form_distance_matrix = list()
        for i in range(len(self.leaf_clusters)):
            row = list()
            for k in range(len(self.leaf_clusters)):
                distance = self.get_distance(self.leaf_clusters[i], self.leaf_clusters[k])
                row.append(distance)
            square_form_distance_matrix.append(row)
        return square_form_distance_matrix

    def get_average_distance(self, index):
        distance_sum = 0
        cluster_size = 1
        for i in range(len(self.object_to_cluster_index)):
            if self.object_to_cluster_index[i] == self.object_to_cluster_index[index]:
                distance_sum += self.square_form_distance_matrix[i][index]
                cluster_size += 1
        return float(distance_sum) / cluster_size

    def get_min_distance(self, index):
        return min(self.square_form_distance_matrix[i][index] \
                        for i in range(len(self.object_to_cluster_index)) \
                        if self.object_to_cluster_index[i] == self.object_to_cluster_index[index] and i != index)


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
            features = o1.build_features(o2)
            X.append(features)
            if mark == "YES":
                logger.debug("{} {} -> YES".format(id1, id2))
                y.append(1)
            elif mark == "NO":
                logger.debug("{} {} -> NO".format(id1, id2))
                y.append(0)
        except django.core.exceptions.ObjectDoesNotExist as e:
            missing_cnt += 1
            logger.debug("skip pair {0} {1}, since one them is not found in DB".format(id1, id2))

    logger.info("convert pool to dedupe: pool size = {0}, missing_count={1}".format(
        processed_cnt, missing_cnt
    ))
    return single_objects, X, y


class TMLModel:
    def __init__(self, filename):
        self.file_name = filename
        with open(filename, 'rb') as sf:
            self.ml_model = pickle.load(sf)

    def predict_positive(self, X):
        return list(p1 for p0, p1 in self.ml_model.predict_proba(X))

    def get_ml_score(self, o1, o2):
        if o1.record_id > o2.record_id:
            o1, o2 = o2, o1
        features = o1.build_features(o2)
        return self.predict_positive([features])[0]

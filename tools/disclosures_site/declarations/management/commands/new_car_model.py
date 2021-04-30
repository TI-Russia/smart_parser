from common.logging_wrapper import setup_logging
from declarations.car_brands import CAR_BRANDS
import declarations.models as models
from declarations.gender_recognize import TGender
from declarations.rubrics import get_all_rubric_ids

from django.core.management import BaseCommand
from django.db import connection
from itertools import groupby
from operator import itemgetter
import json
from sklearn.ensemble import RandomForestClassifier
import random
from sklearn.metrics import precision_score, accuracy_score, recall_score, f1_score, fbeta_score
from sklearn.model_selection import train_test_split
import numpy as np
import tensorflow as tf
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt
from datetime import datetime
from catboost import CatBoostClassifier, Pool
from catboost.utils import get_roc_curve


def get_income_diff(prev_income, curr_income):
    if prev_income is None or prev_income == 0:
        return 0
    if curr_income is None or curr_income == 0:
        return 1.0
    ratio = float(prev_income) / float(curr_income)
    if ratio > 10:
        ratio = 10
    if ratio < 0.1:
        ratio = 0.1
    return round(ratio / 10.0, 4)


def normalize_integer(i, max_value):
    if i is None:
        return 0
    else:
        return i / float(max_value)


class TRealEstateFactors:
    def __init__(self, square_sum=None, previous_year_square_sum=None, real_estate_count=None):
        self.square_sum = square_sum
        self.previous_year_square_sum = previous_year_square_sum
        self.real_estate_count = real_estate_count

    @classmethod
    def from_json(cls, data):
        return cls(**data)


class TVehiclePurchase:
    MAX_RUBRIC_ID = max(get_all_rubric_ids())
    def __init__(self, positive=None, year=None, year_income=None, previous_year_income=None, car_brand=None,
                 person_id=None, spouse_year_income=None, spouse_previous_year_income=None, year_square_sum=None,
                 previous_year_square_sum=None, spouse_year_square_sum=None,
                 spouse_previous_year_square_sum=None, gender=None, rubric_id=None, region_id=None,
                 min_year=None, real_estate_count=None, spouse_real_estate_count=None,
                 declarant_real_estate=None, spouse_real_estate=None, has_children=None):
        self.positive = positive
        self.year = year
        self.year_income = year_income
        self.previous_year_income = previous_year_income
        self.car_brand = car_brand
        self.person_id = person_id
        self.spouse_year_income = spouse_year_income
        self.spouse_previous_year_income = spouse_previous_year_income
        self.declarant_real_estate = TRealEstateFactors(year_square_sum, previous_year_square_sum, real_estate_count)
        self.spouse_real_estate = TRealEstateFactors(spouse_year_square_sum, spouse_previous_year_square_sum, spouse_real_estate_count)
        if declarant_real_estate is not None:
            self.declarant_real_estate = TRealEstateFactors().from_json(declarant_real_estate)
        if spouse_real_estate is not None:
            self.spouse_real_estate = TRealEstateFactors().from_json(spouse_real_estate)
        self.gender = gender
        self.rubric_id = rubric_id
        self.region_id = region_id
        self.min_year = min_year
        self.has_children = has_children

    @classmethod
    def from_json(cls, data):
        return cls(**data)

    @staticmethod
    def get_feature_names():
        return [
                "year",
                "income_diff",
                "spouse_income_diff",
                "income",
                "square_sum",
                "gender",
                "rubric",
                "region",
                "spouse_square_sum",
                #"has_children"
               ]

    def get_year_feature(self):
        cur_year = datetime.today().year
        min_year = 2010
        if self.year < min_year:
            return 0.0
        elif self.year >= cur_year:
            return 1.0
        else:
            return round((cur_year - self.year) / (cur_year - min_year), 2)

    def get_income_diff_feature(self):
        return get_income_diff(self.previous_year_income, self.year_income)

    def get_spouse_income_feature(self):
        return get_income_diff(self.spouse_previous_year_income, self.spouse_year_income)

    def get_income_feature(self):
        if self.year_income is None or self.year_income <= 0:
            return 0
        max_income = 5000000.0
        v = min(max_income, self.year_income)
        return round(v / max_income, 4)

    def get_realestate_square_sum_feature(self, v):
        if v is None or v <= 0:
            return 0
        max_v = 100000.0
        return round(min(max_v, v) / max_v, 4)

    def get_gender_feature(self):
        if self.gender is None:
            return 0
        elif self.gender == TGender.feminine:
            return 0.5
        else:
            return 1.0

    def build_features(self):
        return [
                self.get_year_feature(),
                self.get_income_diff_feature(),
                self.get_spouse_income_feature(),
                self.get_income_feature(),
                self.get_realestate_square_sum_feature(self.declarant_real_estate.square_sum),
                self.get_gender_feature(),
                normalize_integer(self.rubric_id, self.MAX_RUBRIC_ID),
                normalize_integer(self.region_id, 110),
                self.get_realestate_square_sum_feature(self.spouse_real_estate.square_sum),
                ]


class Command(BaseCommand):
    TRAIN_CLASS_WEIGHTS = {0: 1.0, #negative
                           1: 8.0  #positive
                     }

    TEST_CLASS_WEIGHTS = {0: 1.0, #negative
                     1: 5.0  #positive
                     }

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None
        self.logger = None
        self.roc_plt = self.create_roc_plot()
        self.train_x = None
        self.train_y = None
        self.test_x = None
        self.test_y = None

    def find_vehicle_purchase_year(self):
        query = """
            select person_id, section_id, income_year, v.name
            from declarations_section s
            left join (
                 select section_id, group_concat(name) as name
                 from declarations_vehicle
                 group by section_id
                 ) v on s.id = v.section_id
            where person_id is not null and
                  s.source_document_id in ( select s2.source_document_id from declarations_section s2 
                                             where s2.id in (select section_id from declarations_vehicle))
            order by person_id, income_year
        """
        positive_count = 0
        negative_count = 0
        cases = list()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id, items in groupby(cursor, itemgetter(0)):
                years = set()
                for _, section_id, income_year, vehicle_name in items:
                    if income_year in years:
                        continue
                    years.add(income_year)
                    positive = (vehicle_name is not None)
                    case = TVehiclePurchase(person_id=person_id, positive=positive, year=income_year)
                    if positive:
                        if income_year - 1 in years:
                            brands = CAR_BRANDS.find_brands(vehicle_name)
                            if len(brands) > 0:
                                case.car_brand = brands[0]
                                cases.append(case)
                                positive_count += 1
                        break
                    else:
                        if income_year - 1 in years:
                            negative_count += 1
                            cases.append(case)
        self.logger.info("positive count = {}, negative count = {}".format(positive_count, negative_count))
        return cases

    def write_cases(self, file_name: str, cases):
        self.logger.info("write to {}".format(file_name))
        with open (file_name, "w") as outp:
            for x in cases:
                try:
                    outp.write(json.dumps(x, default=lambda o: o.__dict__) + "\n")
                except Exception as exp:
                    raise

    def read_cases(self, file_name: str, row_count=None):
        cases = list()
        cnt = 0
        with open(file_name, "r") as inp:
            for line in inp:
                cases.append(TVehiclePurchase.from_json(json.loads(line)))
                cnt += 1
                if row_count is not None and cnt >= row_count:
                    break

        self.logger.info("read from {} {} cases".format(file_name, len(cases)))
        return cases

    def init_incomes(self, cases):
        query = """
            select s.person_id, s.income_year, i.size, i.relative
            from declarations_section s
            join declarations_income i on i.section_id = s.id
        """
        incomes = dict()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id, income_year, income_size, relative_code in cursor:
                incomes[(person_id, income_year, relative_code)] = income_size
        c: TVehiclePurchase
        for c in cases:
            c.year_income = incomes.get((c.person_id, c.year, models.Relative.main_declarant_code))
            c.previous_year_income = incomes.get((c.person_id, c.year - 1, models.Relative.main_declarant_code))
            c.spouse_year_income = incomes.get((c.person_id, c.year, models.Relative.spouse_code))
            c.spouse_previous_year_income = incomes.get((c.person_id, c.year - 1, models.Relative.spouse_code))

    def init_real_estate(self, cases, relative_code):
        self.logger.info("init_real_estate")
        assert relative_code in {models.Relative.main_declarant_code, models.Relative.spouse_code}
        query = """
            select  s.person_id, 
                    s.income_year, 
                    sum(r.square) * count(distinct r.id) / count(*),
                    count(distinct r.id)
            from declarations_section s
            join declarations_realestate r on r.section_id = s.id
            where r.relative = "{}"
            group by s.id
        """.format(relative_code)
        squares = dict()
        counts = dict()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id, income_year, real_estate_square, real_estate_cnt in cursor:
                if real_estate_square is not None:
                    squares[(person_id, income_year)] = int(real_estate_square)
                    counts[(person_id, income_year)] = real_estate_cnt

        for c in cases:
            f = TRealEstateFactors(
                    squares.get((c.person_id, c.year)),
                    squares.get((c.person_id, c.year)),
                    counts.get((c.person_id, c.year)))
            if relative_code == models.Relative.main_declarant_code:
                c.declarant_real_estate = f
            else:
                c.spouse_real_estate = f

    def init_section_params(self, cases):
        self.logger.info("init_section_params")
        query = """
            select  s.person_id,
                    s.gender, 
                    s.rubric_id,
                    o.region_id,
                    s.income_year
            from declarations_section s
            join declarations_source_document d on d.id = s.source_document_id
            join declarations_office o on o.id = d.office_id
            where s.person_id is not null
        """
        genders = dict()
        rubrics = dict()
        regions = dict()
        min_year = dict()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id, gender, rubric_id, region_id, income_year in cursor:
                genders[(person_id, income_year)] = gender
                rubrics[(person_id, income_year)] = rubric_id
                regions[(person_id, income_year)] = region_id
                if person_id not in min_year:
                    min_year[person_id] = income_year
                else:
                    min_year[person_id] = min(min_year[person_id], income_year)

        for c in cases:
            c.gender = genders.get((c.person_id, c.year))
            c.rubric_id = rubrics.get((c.person_id, c.year))
            c.region_id = regions.get((c.person_id, c.year))
            c.min_year = min_year[c.person_id]

    def init_children(self, cases):
        self.logger.info    ("init_children")
        person_id_with_children = set()
        for table_name in ['declarations_realestate', 'declarations_vehicle', 'declarations_income']:
            query = """
                select distinct person_id 
                from declarations_section s
                join {} x on s.id = x.section_id
                where x.relative = '{}'
                ;
            """.format(table_name, models.Relative.child_code)
            with connection.cursor() as cursor:
                cursor.execute(query)
                for person_id, in cursor:
                    person_id_with_children.add(person_id)

        for c in cases:
            c.has_children = c.person_id in person_id_with_children

    def get_positive_negative_counts(self, labels):
        positive_count = 0
        negative_count = 0
        for c in labels:
            if c != 0:
                positive_count += 1
            else:
                negative_count += 1
        return positive_count, negative_count

    def to_ml_input(self, cases, name):
        self.logger.info("build {} pool of {} cases".format(name, len(cases)))
        features = list()
        labels = list()
        for c in cases:
            features.append(c.build_features())
            labels.append(1 if c.positive else 0)
        return np.array(features), np.array(labels)

    def print_ml_metrics(self, pool_name, y_predicted, y_true):
        precision = precision_score(y_true, y_predicted)
        recall = recall_score(y_true, y_predicted)
        f1 = f1_score(y_true, y_predicted)
        accuracy = accuracy_score(y_true, y_predicted)
        weights_by_class = [self.TEST_CLASS_WEIGHTS[y] for y in y_true]
        accuracy_weighted = accuracy_score(y_true, y_predicted, sample_weight=weights_by_class)
        predicted_positive_count, predicted_negative_count = self.get_positive_negative_counts(y_predicted)
        true_positive_count, true_negative_count = self.get_positive_negative_counts(y_true)

        self.logger.info("pool={}, precision={:.4f}, accuracy={:.4f}, accuracy_weighted={:.4f} "
                         "recall={:.4f}, f1={:.4f}, "
                         "predicted_positive_count={}, predicted_negative_count={},"
                         " true_positive_count={}, true_negative_count={}".format(
                pool_name, precision, accuracy, accuracy_weighted,
                recall, f1,
                predicted_positive_count, predicted_negative_count,
                true_positive_count, true_negative_count))

    def print_features_mean(self, cases):
        feature_names = TVehiclePurchase.get_feature_names()
        features_count = len(feature_names)
        examples = list(list() for i in range(features_count))
        for c in cases:
            features = c.build_features()
            assert len(features) == features_count
            for i in range(features_count):
                examples[i].append(features[i])
        for i in range(features_count):
            print("feature {}: mean={:.4f}, min={}, max={}".format(feature_names[i], np.mean(examples[i]),
                                                           min(examples[i]), max(examples[i]))
                  )

    def train_random_forest(self, trees_count=200):
        self.logger.info("train_random_forest")
        model = RandomForestClassifier(
            n_jobs=3, n_estimators=trees_count, min_samples_leaf=100,
            class_weight={0: 1.0, 1: 5.0}
        )

        self.logger.info("RandomForestClassifier.fit (trees_count={})...".format(trees_count))
        model.fit(self.train_x, self.train_y)

        #export_graphviz(ml_model.estimators_[0],
        #                out_file='tree.dot',
        #                feature_names=TVehiclePurchase.get_feature_names(),
        #                #class_names=iris.target_names,
        #                rounded=True, proportion=False,
        #                precision=2, filled=True)
        for name, value in zip(TVehiclePurchase.get_feature_names(), model.feature_importances_):
            self.logger.info("importance[{}] = {}".format(name, round(value, 3)))
        self.logger.info("ml params = {}".format(model.get_params()))
        self.print_ml_metrics("train", model.predict(self.train_x),  self.train_y)
        self.print_ml_metrics("test", model.predict(self.test_x), self.test_y)
        test_y_pred_proba = model.predict_proba(self.test_x)[:,1]
        fpr, tpr, thresholds = roc_curve(self.test_y, test_y_pred_proba)
        self.show_roc_curve("randomforest_{}".format(trees_count), fpr, tpr)

    def create_roc_plot(self):
        plt.figure(1)
        plt.plot([0, 1], [0, 1], 'k--')
        plt.xlabel('False positive rate')
        plt.ylabel('True positive rate')
        plt.title('ROC curve')

        return plt

    def show_roc_curve(self, model_name, fpr, tpr):
        self.roc_plt.plot(fpr, tpr, label='{} (area = {:.3f})'.format(model_name, auc(fpr, tpr)))

    def find_threshold_tf(self, train_y_predicted, y_true):
        return 0.6

        max_f1 = 0
        best_threshold = 0
        tp, tn = self.get_positive_negative_counts(y_true)
        #train_y_predicted = list(x[0] for x in train_y_predicted)
        for threshold in np.arange(0.50, 0.70, 0.001):
            y_predicted = np.where(train_y_predicted < threshold, 0, 1)
            pos, neg = self.get_positive_negative_counts(y_predicted)
            f1 = fbeta_score(y_true, y_predicted, beta=1.0)
            print("t={:.6f} f1={:.6f} prec={:.6f} recall={:.6f} neg={}, pos={}, tp={}".format(
                threshold, f1,
                precision_score(y_true, y_predicted),
                recall_score(y_true, y_predicted),
                neg, pos, tp))
            if f1 > max_f1:
                max_f1 = f1
                best_threshold = threshold
        return best_threshold

    def train_tensorflow(self, epochs_count=10):
        batch_size = 512
        self.logger.info("train_tensorflow")

        #initial_bias = np.log([pos / neg])
        #output_bias = tf.keras.initializers.Constant(initial_bias)

        model = tf.keras.Sequential([
             tf.keras.layers.Dense(64, activation='relu', input_shape=(self.train_x.shape[-1],)),
             tf.keras.layers.Dense(64),
             tf.keras.layers.Dropout(0.5),
             #tf.keras.layers.Dense(1, activation="sigmoid", bias_initializer=output_bias)
             tf.keras.layers.Dense(1, activation="sigmoid")
        ])

        model.compile(optimizer='adam',
                      loss=tf.keras.losses.BinaryCrossentropy(),
                      weighted_metrics=['accuracy'])

        model.fit(self.train_x, self.train_y, epochs=epochs_count,
                  class_weight=self.TRAIN_CLASS_WEIGHTS,
                  workers=3,
                  batch_size=batch_size,
                  validation_split=0.2)
        train_y_predicted = model.predict(self.train_x, batch_size=batch_size).ravel()
        threshold = self.find_threshold_tf(train_y_predicted, self.train_y)
        print("threshold={}".format(threshold))
        #threshold = 0.445
        def predict_tf(x):
            return np.where(model.predict(x, batch_size=batch_size).ravel() < threshold, 0, 1)
        self.print_ml_metrics("train", predict_tf(self.train_x),  self.train_y)
        self.print_ml_metrics("test", predict_tf(self.test_x), self.test_y)

        test_y_pred = model.predict(self.test_x).ravel()
        fpr, tpr, thresholds = roc_curve(self.test_y, test_y_pred)
        self.show_roc_curve("tensorflow_{}".format(epochs_count), fpr, tpr)

    def train_catboost(self, iter_count=100):
        self.logger.info("train_catboost iterations count={}".format(iter_count))

        model = CatBoostClassifier(iterations=iter_count,
                                   depth=4,
                                   #learning_rate=0.1,
                                   loss_function='Logloss',
                                   class_weights={0: 1.0, 1: 5.0},
                                   verbose=True)
        model.fit(self.train_x, self.train_y)
        print(model.classes_)
        assert model.classes_[0] == 0
        assert model.classes_[1] == 1
        #threshold = 0.85
        threshold = 0.5
        def predict(x):
            return np.where(model.predict_proba(x)[:,0] > threshold, 0, 1)
        self.print_ml_metrics("train", predict(self.train_x), self.train_y)
        self.print_ml_metrics("test",  predict(self.test_x), self.test_y)

        catboost_pool = Pool(self.test_x, self.test_y)
        fpr, tpr, thresholds = get_roc_curve(model, catboost_pool)
        self.show_roc_curve("catboost_{}".format(iter_count), fpr, tpr)

    def create_test_and_train(self, cases):
        random.shuffle(cases)
        self.print_features_mean(cases[0:1000])
        train, test = train_test_split(cases, test_size=0.2)
        self.train_x, self.train_y = self.to_ml_input(train, "train")
        self.test_x, self.test_y = self.to_ml_input(test, "test")
        pos, neg = self.get_positive_negative_counts(self.train_y)
        print("train distribution: pos={}, neg={} to obtain input bias".format(pos, neg))

    def handle(self, *args, **options):
        self.options = options
        self.logger = setup_logging(logger_name="new_car_model")
        file_name = "new_car_cases.txt"
        # cases = self.find_vehicle_purchase_year()
        # self.write_cases(file_name + ".1", cases)
        #
        # self.init_incomes(cases)
        # self.write_cases(file_name + ".2", cases)
        #cases = self.read_cases(file_name + ".2")
        #
        #self.init_real_estate(cases, models.Relative.main_declarant_code)
        #self.write_cases(file_name + ".3", cases)
        #cases = self.read_cases(file_name + ".3")
        #self.init_section_params(cases)
        #self.write_cases(file_name + ".4", cases)


        #cases = self.read_cases(file_name + ".4")
        #self.init_real_estate(cases, models.Relative.spouse_code)
        #self.write_cases(file_name + ".5", cases)

        #cases = self.read_cases(file_name + ".5")
        #self.init_children(cases)
        #self.write_cases(file_name + ".6", cases)

        #cases = self.read_cases(file_name + ".6", row_count=10000)
        cases = self.read_cases(file_name + ".6")
        self.create_test_and_train(cases)

        #model_size = 2
        model_size = 1
        #model_size = 5
        self.train_random_forest(trees_count=50*model_size)
        self.train_tensorflow(epochs_count=30*model_size)
        self.train_catboost(iter_count=100*model_size)
        self.roc_plt.legend(loc='best')
        self.roc_plt.show(block=True)

from common.logging_wrapper import setup_logging
from declarations.car_brands import CAR_BRANDS
import declarations.models as models

from django.core.management import BaseCommand
from django.db import connection
from itertools import groupby
from operator import itemgetter
import json
from sklearn.ensemble import RandomForestClassifier
import random
from sklearn.metrics import precision_score, accuracy_score
from sklearn.model_selection import train_test_split
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt
import math

# from sklearn.linear_model import LogisticRegression
# from sklearn.tree import export_graphviz
# from sklearn.neural_network import MLPClassifier
# from sklearn import svm
# from sklearn.pipeline import make_pipeline
# from sklearn.preprocessing import StandardScaler
# from sklearn.ensemble import AdaBoostClassifier
#
# from sklearn.experimental import enable_hist_gradient_boosting  # noqa
# from sklearn.ensemble import HistGradientBoostingClassifier


def get_integer_diff(i1, i2):
    if i1 is None or i2 is None:
        return 0
    return round(i1/(i2 + 0.000000001), 1)


def get_integer(i, denominator=1):
    if i is None:
        return 0
    else:
        return int(i / denominator)


class TRealEstateFactors:
    def __init__(self, square_sum=None, previous_year_square_sum=None, real_estate_count=None):
        self.square_sum = square_sum
        self.previous_year_square_sum = previous_year_square_sum
        self.real_estate_count = real_estate_count

    @classmethod
    def from_json(cls, data):
        return cls(**data)


class TVehiclePurchase:
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

    def build_features(self):
        return [
                self.year,
                get_integer_diff(self.previous_year_income, self.year_income),
                get_integer_diff(self.spouse_previous_year_income, self.spouse_year_income),
                get_integer(self.year_income, 100),
                get_integer(self.declarant_real_estate.square_sum),
                get_integer(self.gender),
                get_integer(self.rubric_id),
                get_integer(self.region_id),
                get_integer(self.spouse_real_estate.square_sum),
                #(1 if self.has_children else 0)
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
        accuracy = accuracy_score(y_true, y_predicted)
        weights_by_class = [self.TEST_CLASS_WEIGHTS[y] for y in y_true]
        accuracy_weighted = accuracy_score(y_true, y_predicted, sample_weight=weights_by_class)
        predicted_positive_count, predicted_negative_count = self.get_positive_negative_counts(y_predicted)
        true_positive_count, true_negative_count = self.get_positive_negative_counts(y_true)

        self.logger.info("pool={}, precision={:.4f}, accuracy={:.4f}, accuracy_weighted={:.4f} "
                         "predicted_positive_count={}, predicted_negative_count={},"
                         " true_positive_count={}, true_negative_count={}".format(
                pool_name, precision, accuracy, accuracy_weighted,
                predicted_positive_count, predicted_negative_count,
                true_positive_count, true_negative_count))

    def train_random_forest(self, train, test, trees_count=200):
        self.logger.info("train_random_forest")
        train_x, train_y = self.to_ml_input(train, "train")
        test_x, test_y = self.to_ml_input(test, "test")
        ml_model = RandomForestClassifier(
            n_jobs=3, n_estimators=trees_count, min_samples_leaf=100,
            class_weight=self.TRAIN_CLASS_WEIGHTS)

        self.logger.info("RandomForestClassifier.fit (trees_count={})...".format(trees_count))
        ml_model.fit(train_x, train_y)

        #export_graphviz(ml_model.estimators_[0],
        #                out_file='tree.dot',
        #                feature_names=TVehiclePurchase.get_feature_names(),
        #                #class_names=iris.target_names,
        #                rounded=True, proportion=False,
        #                precision=2, filled=True)
        for name, value in zip(TVehiclePurchase.get_feature_names(), ml_model.feature_importances_):
            self.logger.info("importance[{}] = {}".format(name, round(value, 3)))
        self.logger.info("ml params = {}".format(ml_model.get_params()))
        self.print_ml_metrics("train", ml_model.predict(train_x),  train_y)
        self.print_ml_metrics("test", ml_model.predict(test_x), test_y)

    def show_tf_roc_curve(self, model, test_x, test_y):
        y_pred_keras = model.predict(test_x).ravel()
        fpr_keras, tpr_keras, thresholds_keras = roc_curve(test_y, y_pred_keras)
        gmeans = np.sqrt(tpr_keras * (1 - fpr_keras))
        ix = np.argmax(gmeans)
        print('Best Threshold={}, G-Mean={:.3f}'.format(thresholds_keras[ix], gmeans[ix]))
        auc_keras = auc(fpr_keras, tpr_keras)
        plt.figure(1)
        plt.plot([0, 1], [0, 1], 'k--')
        plt.plot(fpr_keras, tpr_keras, label='Keras (area = {:.3f})'.format(auc_keras))
        plt.xlabel('False positive rate')
        plt.ylabel('True positive rate')
        plt.title('ROC curve')
        plt.legend(loc='best')
        plt.show()

    def train_tensorflow(self, train, test, epochs_count=10):
        self.logger.info("train_tensorflow")

        train_x, train_y = self.to_ml_input(train, "train")
        test_x, test_y = self.to_ml_input(test, "test")
        #neg, pos = np.bincount(train_y)
        #initial_bias = np.log([pos / neg])
        #initial_bias = 1.0 / 1.0
        #output_bias = tf.keras.initializers.Constant(initial_bias)

        scaler = StandardScaler()
        train_x = scaler.fit_transform(train_x)
        test_x = scaler.transform(test_x)

        model = tf.keras.Sequential([
             tf.keras.layers.Flatten(input_shape=(9,)),
             tf.keras.layers.Dense(128, activation='relu'),
             tf.keras.layers.Dropout(0.5),
             tf.keras.layers.Dense(1, activation="sigmoid"
                                   #, bias_initializer=output_bias
                                   )
        ])
        # tf.keras.layers.Dense(2)

        model.compile(optimizer='adam',
                      #loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                      loss=tf.keras.losses.BinaryCrossentropy(),
                      #loss=tf.keras.losses.MeanAbsoluteError(),
                      weighted_metrics=['accuracy'])

        model.fit(train_x, train_y, epochs=epochs_count,
                  class_weight=self.TRAIN_CLASS_WEIGHTS, workers=3,
                  validation_split=0.2)

        def predict_tf(x):
            #return model.predict(x).argmax(axis=-1)
            return np.where(model.predict(x) < 0.5, 0, 1)
        #debug = model.predict(train_x)
        #debug1 = np.where(debug < 0.5, 0, 1)
        self.print_ml_metrics("train", predict_tf(train_x),  train_y)
        self.print_ml_metrics("test", predict_tf(test_x), test_y)
        self.show_tf_roc_curve(model, test_x, test_y)

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

        #cases = self.read_cases(file_name + ".6", row_count=1000)
        cases = self.read_cases(file_name + ".6")
        random.shuffle(cases)
        train, test = train_test_split(cases, test_size=0.2)
        #self.train_random_forest(train, test)
        self.train_tensorflow(train, test, epochs_count=10)

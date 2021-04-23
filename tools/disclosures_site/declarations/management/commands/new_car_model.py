from common.logging_wrapper import setup_logging
from declarations.car_brands import CAR_BRANDS
import declarations.models as models

from django.core.management import BaseCommand
from django.db import connection
from itertools import groupby
from operator import itemgetter
import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import random
from sklearn.metrics import precision_score
from sklearn.tree import export_graphviz


def get_integer_diff(i1, i2):
    if i1 is None or i2 is None:
        return 0
    return round(i1/(i2 + 0.000000001), 1)


def get_integer(i):
    if i is None:
        return 0
    else:
        return int(i)


class TVehiclePurchase:
    def __init__(self, positive=None, year=None, year_income=None, previous_year_income=None, car_brand=None,
                 person_id=None, spouse_year_income=None, spouse_previous_year_income=None, year_square_sum=None,
                 previous_year_square_sum=None, spouse_year_square_sum=None,
                 spouse_previous_year_square_sum=None):
        self.positive = positive
        self.year = year
        self.year_income = year_income
        self.previous_year_income = previous_year_income
        self.car_brand = car_brand
        self.person_id = person_id
        self.spouse_year_income = spouse_year_income
        self.spouse_previous_year_income = spouse_previous_year_income
        self.year_square_sum = year_square_sum
        self.previous_year_square_sum = previous_year_square_sum
        self.spouse_year_square_sum = spouse_year_square_sum
        self.spouse_previous_year_square_sum = spouse_previous_year_square_sum

    @classmethod
    def from_json(cls, data):
        return cls(**data)

    @staticmethod
    def get_feature_names():
        return [
                "year",
                "income_diff",
                "spouse_income_diff",
                #"square_diff",
                #"income",
                #"square_sum",
               ]

    def build_features(self):
        return [
                self.year,
                get_integer_diff(self.previous_year_income, self.year_income),
                get_integer_diff(self.spouse_previous_year_income, self.spouse_year_income),
                #get_integer_diff(self.previous_year_square_sum, self.year_square_sum),
                #get_integer(self.year_income/300000),
                #get_integer(self.year_square_sum)
               ]


class Command(BaseCommand):

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
            where person_id is not null
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

    def read_cases(self, file_name: str):
        self.logger.info("read from {}".format(file_name))
        cases = list()
        with open(file_name, "r") as inp:
            for line in inp:
                cases.append(TVehiclePurchase.from_json(json.loads(line)))
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
        assert relative_code in {models.Relative.main_declarant_code, models.Relative.spouse_code}
        query = """
            select  s.person_id, 
                    s.income_year, 
                    sum(r.square) * count(distinct r.id) / count(*)
            from declarations_section s
            join declarations_realestate r on r.section_id = s.id
            where r.relative = "{}"
            group by s.id
        """.format(relative_code)
        values = dict()
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id, income_year, real_estate_square in cursor:
                if real_estate_square is not None:
                    values[(person_id, income_year)] = int(real_estate_square)

        if relative_code == models.Relative.main_declarant_code:
            for c in cases:
                c.year_square_sum = values.get((c.person_id, c.year))
                c.previous_year_square_sum = values.get((c.person_id, c.year - 1))
        else:
            for c in cases:
                c.spouse_year_square_sum = values.get((c.person_id, c.year))
                c.spouse_previous_year_square_sum = values.get((c.person_id, c.year - 1))

    def to_ml_input(self, cases, name):
        X = list()
        Y = list()
        positive_count = 0
        negative_count = 0
        for c in cases:
            X.append(c.build_features())
            Y.append(1 if c.positive else 0)
            if c.positive:
                positive_count += 1
            else:
                negative_count += 1
        self.logger.info("pool {}: positive_count={}, negative_count={}".format(name, positive_count, negative_count))

        return X, Y

    def test_ml(self, ml_model, pool_name, x, y_true):
        self.logger.info("test ml on {} ({} cases)".format(pool_name,  len(x)))
        y_predicted = ml_model.predict(x)
        precision = precision_score(y_true, y_predicted)
        positive_count = 0
        negative_count = 0
        for c in y_predicted:
            if c != 0:
                positive_count += 1
            else:
                negative_count += 1

        self.logger.info("precision on {} = {}, positive_count={}, negative_count={}".format(
                pool_name, precision, positive_count, negative_count))

    def train_ml(self, cases):
        #sample_size = 30000
        sample_size = 400000
        self.logger.info("train ml on {} cases out of {} cases...".format(sample_size, len(cases)))
        random.shuffle(cases)
        X_train, Y_train = self.to_ml_input(cases[0:sample_size], "train")
        X_test, Y_test = self.to_ml_input(cases[-sample_size:], "test")
        #ml_model = RandomForestClassifier(n_estimators=300, max_depth=3, random_state=0)
        #ml_model = RandomForestClassifier(n_estimators=4, max_depth=5)
        #ml_model = LogisticRegression(max_iter=500)
        ml_model = RandomForestClassifier(n_estimators=100, class_weight={0:1, 1:5})
        ml_model.fit(X_train, Y_train)

        #export_graphviz(ml_model.estimators_[0],
        #                out_file='tree.dot',
        #                feature_names=TVehiclePurchase.get_feature_names(),
        #                #class_names=iris.target_names,
        #                rounded=True, proportion=False,
        #                precision=2, filled=True)

        #self.logger.info("feature_importances_ = {}".format(
         #   list(zip(TVehiclePurchase.get_feature_names(), ml_model.feature_importances_))))
        self.logger.info("ml params = {}".format(ml_model.get_params()))

        self.test_ml(ml_model, "train", X_train, Y_train)
        self.test_ml(ml_model, "test", X_test, Y_test)


    def handle(self, *args, **options):
        self.options = options
        self.logger = setup_logging(logger_name="new_car_model")
        file_name = "new_car_cases.txt"
        #cases = self.find_vehicle_purchase_year()
        #self.write_cases(file_name + ".1", cases)

        #self.init_incomes(cases)
        #self.write_cases(file_name + ".2", cases)
        #cases = self.read_cases(file_name + ".2")

        #self.init_real_estate(cases, models.Relative.main_declarant_code)
        #self.write_cases(file_name + ".3", cases)
        cases = self.read_cases(file_name + ".3")
        self.train_ml(cases)

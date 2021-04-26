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
from sklearn.metrics import precision_score

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

    def read_cases(self, file_name: str):
        cases = list()
        with open(file_name, "r") as inp:
            for line in inp:
                cases.append(TVehiclePurchase.from_json(json.loads(line)))
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
        self.logger.info("train_ml")
        #sample_size = 30000
        sample_size = 400000
        random.shuffle(cases)
        X_train, Y_train = self.to_ml_input(cases[0:sample_size], "train")
        X_test, Y_test = self.to_ml_input(cases[-sample_size:], "test")
        ml_model = RandomForestClassifier(n_jobs=3, n_estimators=200, min_samples_leaf=100, class_weight={0: 1, 1: 5})


        self.logger.info("train ml on {} cases out of {} cases...".format(sample_size, len(cases)))
        ml_model.fit(X_train, Y_train)

        #export_graphviz(ml_model.estimators_[0],
        #                out_file='tree.dot',
        #                feature_names=TVehiclePurchase.get_feature_names(),
        #                #class_names=iris.target_names,
        #                rounded=True, proportion=False,
        #                precision=2, filled=True)
        for name, value in zip(TVehiclePurchase.get_feature_names(), ml_model.feature_importances_):
            self.logger.info("importance[{}] = {}".format(name, round(value, 3)))
        self.logger.info("ml params = {}".format(ml_model.get_params()))

        self.test_ml(ml_model, "train", X_train, Y_train)
        self.test_ml(ml_model, "test", X_test, Y_test)


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

        cases = self.read_cases(file_name + ".6")
        self.train_ml(cases)

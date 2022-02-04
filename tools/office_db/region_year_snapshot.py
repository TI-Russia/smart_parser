from office_db.region_data import TRossStatData

import os
from statistics import median
import json
import scipy.stats


class TRegionYearStats:
    def  __init__(self, region_id=None, region_name=None, incomes=None, citizen_month_median_salary=None, population=None,
                 er_election=None):
        self.region_id = region_id
        self.region_name = region_name
        self.citizen_month_median_salary = citizen_month_median_salary
        self.population = population
        self.er_election = er_election
        #aux_params
        self.declarant_month_median_income = None
        self.declarant_count = None
        self.efficiency = None
        #runtime
        self.incomes = incomes

    def calc_aux_params(self):
        self.declarant_month_median_income = int(median(self.incomes) / 12)
        self.declarant_count = len(self.incomes)
        self.efficiency = int(sum(self.incomes) / self.population)
        del self.incomes

    def to_json(self):
        return {
            'region_id': self.region_id,
            'region_name': self.region_name,
            'citizen_month_median_salary': self.citizen_month_median_salary,
            'population': self.population,
            'declarant_month_median_income': self.declarant_month_median_income,
            'declarant_count': self.declarant_count,
            'efficiency': self.efficiency,
            'er_election': self.er_election
        }

    def get_inequality(self):
        return round(self.declarant_month_median_income/self.citizen_month_median_salary, 2)

    def get_table_cells(self):
        return (self.region_id,
                self.region_name,
                self.declarant_month_median_income,
                self.citizen_month_median_salary,
                self.get_inequality(),
                self.declarant_count,
                self.population,
                round(self.declarant_count / self.population, 4),
                self.efficiency,
                self.er_election
                )

    @staticmethod
    def get_table_column_description():
            return ("Идентификатор региона",
                    "Название региона",
                    "Медианный доход чиновника (декларанта) в месяц в регионе",
                    "Медианная зарплата граждан в регионе",
                    "Медианный доход чиновника, поделенный на медианную зарплату граждан",
                    "Количество учтенных деклараций",
                    "Численность населения",
                    "Количество учтенных деклараций, поделенное на численность населения",
                    "Сумма доходов чиновников, поделенная на численность населения",
                    "Поддержка Единой России на последних выборах в Госдуму (проценты)")

    @staticmethod
    def get_table_headers():
            return ("Id",
                    "Region", "MeD", "MeP",
            "Ineq",
            "DecCnt", "Population",
            "DecDens", "IncomeDens", "ER")

    @staticmethod
    def from_json(j):
        r = TRegionYearStats()
        r.region_id = j['region_id']
        r.region_name = j['region_name']
        r.citizen_month_median_salary = j['citizen_month_median_salary']
        r.population = j['population']
        r.declarant_month_median_income = j['declarant_month_median_income']
        r.declarant_count = j['declarant_count']
        r.efficiency = j['efficiency']
        r.er_election = j['er_election']
        return r


class TAllRegionStatsForOneYear:

    def __init__(self, year, file_name=None, regions=None):
        self.year = year
        self.data_by_region = None
        if file_name is None:
            self.file_name = os.path.join(os.path.dirname(__file__), 'data/region_report_table_{}.json'.format(year))
        else:
            self.file_name = file_name
        self.ross_stat = TRossStatData(regions=regions)
        self.ross_stat.load_from_disk()
        self.corr_matrix = None

    def load_from_disk(self):
        with open(self.file_name) as inp:
            data = json.load(inp)
            self.data_by_region = dict((int(k), TRegionYearStats.from_json(v)) for k, v in data.items())

    def get_region_info(self, region_id) -> TRegionYearStats:
        return self.data_by_region.get(int(region_id))

    def write_to_disk(self):
        with open(self.file_name, "w") as outp:
            d = dict((k, v.to_json()) for k,v in self.data_by_region.items())
            json.dump(d, outp, indent=4, ensure_ascii=False)

    def add_snapshot(self, d: TRegionYearStats):
        if d.region_id in self.data_by_region:
            self.data_by_region[d.region_id].incomes.extend(d.incomes)
        else:
            self.data_by_region[d.region_id] = d

    def calc_aux_params(self):
        for k, v in self.data_by_region.items():
            v.calc_aux_params()

    def build_correlation_matrix(self):
        data = list(k.get_table_cells() for k in self.data_by_region.values())
        cnt = len(data[0])
        corr_matrix = list([''] * (cnt+1) for i in range(0, cnt))
        for i in range(0, cnt):
            corr_matrix[i][0] = TRegionYearStats.get_table_headers()[i]
        for i in range(0, cnt):
            for k in range(i+1, cnt):
                if i != 1 and k != 1:
                    x = list(d[i] for d in data)
                    y = list(d[k] for d in data)
                    rho, pval = scipy.stats.spearmanr(x, y)
                    corr_matrix[i][k+1] = "rho={:.2f}, pval={:.3f}".format(rho, pval) # k+1 - first column is a name
        self.corr_matrix = corr_matrix

from office_db.year_income import TYearIncome
from office_db.rubrics import get_russian_rubric_str

import json
import os


class TGroupYearSnapshot:
    def __init__(self, median_income=None, incomes_count=None):
        self.median_year_income = median_income
        self.incomes_count = incomes_count

    @staticmethod
    def from_json(j):
        d = TGroupYearSnapshot()
        d.incomes_count = j.get('incomes_count')
        d.median_year_income = j.get('median_year_income')
        return d

    def to_json(self):
        return {
            'incomes_count': self.incomes_count,
            'median_year_income': self.median_year_income
        }


class TGroupStatData:
    def __init__(self):
        self.year_snapshots = dict()
        self.v2 = None
        self.v_size = None

    def get_office_snapshot(self, year) -> TGroupYearSnapshot:
        return self.year_snapshots.get(year)

    def is_empty(self):
        return len(self.year_snapshots) == 0

    @staticmethod
    def from_json(j):
        d = TGroupStatData()
        d.year_snapshots = dict((int(k), TGroupYearSnapshot.from_json(v)) for k,v in j['year_snapshots'].items())
        d.v2 = j.get('V2')
        d.v2_size = j.get('V2_size')
        return d

    def to_json(self):
        return {
            'year_snapshots': dict((k, v.to_json()) for k,v in self.year_snapshots.items()),
            'V2': self.v2,
            'V2_size': self.v2_size
        }

    def add_snapshot(self, year: int, snapshot: TGroupYearSnapshot):
        self.year_snapshots[year] = snapshot

    def get_median_income(self, year: int):
        a = self.year_snapshots.get(year)
        if a is None:
            return None
        return a.median_year_income


class TGroupStatDataList:
    office_group = 1
    rubric_group = 2

    def __init__(self, directory, group_type=None, start_year=None, last_year=None):
        self.declarant_groups = dict()
        self.group_type = group_type
        self.start_year = start_year
        self.last_year = last_year
        if self.group_type is  None:
            self.group_type = TGroupStatDataList.office_group
        if self.group_type == TGroupStatDataList.office_group:
            self.file_path = os.path.join(directory, "office_stat_data.txt")
        else:
            self.file_path = os.path.join(directory, "rubric_stat_data.txt")

    def get_csv_path(self):
        return self.file_path[:-len('.txt')] + ".csv"

    def write_csv_file(self, russia, filepath=None):
        if filepath is None:
            filepath = self.get_csv_path()
        with open(filepath, "w") as outp:
            outp.write("\t".join(self.get_table_headers()) + "\n")
            for r in self.get_all_office_report_rows(russia):
                outp.write("\t".join(map(str, r)) + "\n")

    def load_from_disk(self):
        self.declarant_groups = dict()
        with open(self.file_path) as inp:
            j = json.load(inp)
            for k, v in j['groups'].items():
                if k == "null":
                    k = None
                else:
                    k = int(k)
                self.declarant_groups[k] = TGroupStatData.from_json(v)
            self.start_year = j['start_year']
            self.last_year = j['last_year']

    def save_to_disk(self, postfix=""):
        with open(self.file_path + postfix, "w") as outp:
            d = {
               "groups":  dict( (k, v.to_json()) for k, v in self.declarant_groups.items()),
               'start_year': self.start_year,
               'last_year': self.last_year
            }
            json.dump(d, outp, indent=4, ensure_ascii=False)

    def add_group(self, group_id: int, group: TGroupStatData):
        self.declarant_groups[group_id] = group

    def get_group_data(self, group_id: int) -> TGroupStatData:
        return self.declarant_groups.get(group_id)

    def get_table_headers(self):
        l = ['Id', 'Name']
        for year in range(self.start_year, self.last_year + 1):
            l.append(str(year))
            l.append('|{}|'.format(year))
        l.append('Q1')
        l.append('PI')
        l.append('D1')
        l.append('V2')
        l.append('|V2|')
        return l

    def get_table_column_description(self):
        l = ['Идентификатор',
             'Название']
        for year in range(self.start_year, self.last_year + 1):
            l.append("Медианный доход за {} год".format(year))
            l.append('Количество учтенных деклараций за {} год'.format(year))
        l.append('Во сколько раз сотрудники ведомства получают больше населения (посл. учтенный год)')
        l.append('Рост медианной зарплаты всего населения в процентах в пределах учтенного интервала')
        l.append('Рост медианного дохода декларантов в процентах в пределах учтенного интервала')
        l.append('Усредненный индивидуальный рост декларантов в пределах учтенного интервала, поделенный на средний рост зарплаты населения')
        l.append('Количество элементов, учтенных в V2')
        return l

    def get_office_report_table_row(self, russia, group_id, max_cell_width=None):
        if  self.group_type == TGroupStatDataList.office_group:
            name = russia.get_office(group_id).name
            if max_cell_width is not None:
                if len(name) > max_cell_width - 3:
                    name = name[:max_cell_width - 3] + "..."
            output_row = [group_id, name]
        else:
            if group_id is None:
                rubric_name = "остальное"
            else:
                rubric_name = get_russian_rubric_str(group_id)
            output_row = [group_id, rubric_name]
        office_info: TGroupStatData
        office_info = self.declarant_groups.get(group_id)
        if office_info is None:
            return None
        declarant_count = 0
        year_count = 0
        valid_incomes = list()
        for year in range(self.start_year, self.last_year + 1):
            d = office_info.get_office_snapshot(year)
            if d is not None and d.incomes_count > 5:
                declarant_count += d.incomes_count
                year_count += 1
                output_row.append(d.median_year_income)
                output_row.append(d.incomes_count)
                valid_incomes.append(TYearIncome(year, d.median_year_income))
            else:
                output_row.append(-1)
                output_row.append(0)

        if declarant_count <= 10 or year_count < 2:
            # office is too small
            return None

        cmp_result = russia.get_average_nominal_incomes(valid_incomes)
        if cmp_result is None:
            params = [-1] * 4
        else:
            Q1 = russia.compare_to_all_russia_average_month_income(
                          valid_incomes[-1].year,
                          valid_incomes[-1].income/12.0)
            Q1_str = str(Q1).replace(".", ",")
            PI = cmp_result.population_income_growth
            D1 = cmp_result.declarant_income_growth
            V2_str = str(office_info.v2).replace(".", ",")
            params = [Q1_str, PI, D1, V2_str, office_info.v2_size]
        output_row.extend(params)
        return output_row

    def get_all_office_report_rows(self, russia):
        for group_id in self.declarant_groups.keys():
            r = self.get_office_report_table_row(russia, group_id, max_cell_width=120)
            if r is not None:
                yield r


class TOfficeRubricCalculatedData:
    def __init__(self, directory):
        self.directory = directory
        self.office_stats = TGroupStatDataList(directory, TGroupStatDataList.office_group)
        self.office_stats.load_from_disk()

        self.rubric_stats = TGroupStatDataList(directory, TGroupStatDataList.rubric_group)
        self.rubric_stats.load_from_disk()
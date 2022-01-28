from office_db.russian_regions import TRussianRegions

import json
import os


# 1. Население по регионам берется с сайта  rosstat.  Смотри скрипт disclosures_site/scripts/region_report

# 2. Медианная зарплата до 2019 года взята с сайта https://russia.duck.consulting/maps/105/2019 , туда она попала
# из Росстата (там выборка большая, 100000 предприятий, 27 млн. человек). В 2021 году я увидел, russia.duck.consulting тормозит
# и не распарсил дату от Росстата, пришлось лезть самому. Место публикации https://rosstat.gov.ru/compendium/document/13268
# "Сведения о распределении численности работников по размерам заработной платы" (31 таблица). У меня есть скрипт,
# который  парсит эту 31 таблицу (tools/disclosures_site/scripts/rosstat/add_median_year.py)
# Сведения про медиану публикуются раз в два года, обследование проходит раз в апреле.

#3. Среднедушевой доход берется от Росстата https://rosstat.gov.ru/folder/11109/document/13259 ,  таблица 11-01
#  будем усреднять его по всем кварталам. Для четных лет, когда нет медианного исследования от Росстата,
#  будем "восстанавливать" медианную зарплату из среднедушевого дохода простым
#  умножением на K, где К = медиана за прошлый год поделить на среднедушевой год за прошлый год.  Нужно проверить,
# как это коэффициент работает (какая там ошибка)


class TRegionYearInfo:
    def __init__(self, population=None, median_salary=None, average_income=None):
        self.population = population
        self.median_salary = median_salary
        self.average_income = average_income

    @staticmethod
    def from_json(j):
        r = TRegionYearInfo()
        r.median_salary = j.get('median_salary')
        if r.median_salary is not None:
            assert r.median_salary > 5000
            assert r.median_salary < 300000
        r.population = j.get('population')
        if r.population is not None:
            assert r.population > 10000
        r.average_income = j.get('average_income')
        if r.average_income is not None:
            assert r.average_income > 10000
        return r

    def to_json(self):
        r = dict()
        if self.population is not None:
            r['population'] = self.population
        if self.median_salary is not None:
            r['median_salary'] = self.median_salary
        if self.average_income is not None:
            r['average_income'] = self.average_income
        return r


class TRossStatData:
    def __init__(self):
        self.region_stat = dict()
        self.regions = TRussianRegions()
        self.file_path = os.path.join(os.path.dirname(__file__), "../data/ross_stat.json")

    def load_from_disk(self):
        with open(self.file_path) as inp:
            for key, years in json.load(inp).items():
                region = self.regions.region_id_to_region[int(key)]
                assert region is not None
                region_id = region.id
                if region_id not in self.region_stat:
                    self.region_stat[region_id] = dict()
                for year, stat in years.items():
                    self.region_stat[int(region_id)][int(year)] = TRegionYearInfo.from_json(stat)

    def save_to_disk(self, postfix=""):
        d = dict()
        with open(self.file_path + postfix, "w") as outp:
            for region_id, years in self.region_stat.items():
                d[region_id] = dict()
                for year, info in years.items():
                    d[region_id][year] = info.to_json()
            json.dump(d, outp, indent=3, ensure_ascii=False)

    def check(self, year: int):
        for r in self.regions.iterate_regions():
            if r.id not in self.region_stat:
                raise Exception("region {}, region_id={} is missing".format(r.name, r.id))
            if year not in self.region_stat[r.id]:
                raise Exception("year {} region {}, region_id={} is missing".format(year, r.name, r.id))

    def get_data(self, region_id, year: int):
        return self.region_stat.get(region_id, dict()).get(year)

    def set_data(self, region_id, year: int, info: TRegionYearInfo):
        r = self.region_stat.get(region_id)
        assert r is not None
        r[year] = info

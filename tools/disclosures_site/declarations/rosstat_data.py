from office_db.russian_regions import TRussianRegions

import json
import os


class TRegionYearInfo:
    def __init__(self, population=None, median_income=None):
        self.population = population
        self.median_income = median_income

    @staticmethod
    def from_json(j):
        r = TRegionYearInfo()
        r.median_income = j.get('median_income')
        if r.median_income is not None:
            assert r.median_income > 5000
            assert r.median_income < 300000
        r.population = j.get('population')
        if r.population is not None:
            assert r.population > 10000
        return r

    def to_json(self):
        r = dict()
        if self.population is not None:
            r['population'] = self.population
        if self.median_income is not None:
            r['median_income'] = self.median_income
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
                    self.region_stat[region_id][year] = TRegionYearInfo.from_json(stat)

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

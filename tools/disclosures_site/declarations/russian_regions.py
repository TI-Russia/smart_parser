import json
import os


class TRegion:
    def __init__(self):
        self.id = None
        self.name = None
        self.short_name = None
        self.extra_short_name = None
        self.short_name_en = None
        self.extra_short_name_en  = None
        self.name_en = None
        self.name = None

    def from_json(self, r):
        self.id = int(r['id'])

        self.name = r['name']
        self.short_name = r['short_name']
        self.extra_short_name = r['extra_short_name']

        self.name_en = r['name_en']
        self.short_name_en = r['short_name_en']
        self.extra_short_name_en = r['extra_short_name_en']
        return self


class TRussianRegions:
    def __init__(self):
        self.regions = list()
        filepath = os.path.join(os.path.dirname(__file__), "../data/regions.txt")
        with open(filepath) as inp:
            for region in json.load(inp):
                self.regions.append(TRegion().from_json(region))
        self.region_name_to_region = dict()
        self.region_id_to_region = dict()
        for r in self.regions:
            self.region_name_to_region[r.name.lower().strip('*')] = r
            self.region_name_to_region[r.short_name.lower().strip('*')] = r
            self.region_id_to_region[r.id] = r

    def get_region_by_str(self, russian_name):
        russian_name = russian_name.lower()
        if russian_name == "территории за пределами рф":
            return None
        elif russian_name.find('якутия') != -1:
            return self.region_id_to_region[92]
        elif russian_name.find('москва') != -1:
            return self.region_id_to_region[63]
        elif russian_name.find('санкт-петербург') != -1:
            return self.region_id_to_region[1]
        elif russian_name.find('севастополь') != -1:
            return self.region_id_to_region[110]
        elif russian_name.find('ханты') != -1:
            return self.region_id_to_region[108]
        elif russian_name.find('алания') != -1:
            return self.region_id_to_region[17]
        elif russian_name.find(' тыва') != -1:
            return self.region_id_to_region[85]
        elif russian_name.find('карачаево-') != -1:
            return self.region_id_to_region[11]
        elif russian_name.find('северная осетия') != -1:
            return self.region_id_to_region[17]
        return self.region_name_to_region[russian_name]


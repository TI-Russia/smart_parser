from common.primitives import normalize_whitespace

import json
import os
import sys
import ahocorasick


class TRegion:
    def __init__(self):
        self.id = None
        self.name = None
        self.short_name = None
        self.extra_short_name = None
        self.short_name_en = None
        self.name_en = None
        self.name = None
        self.wikidata_id = None
        self.capital_coords = None
        self.dative_forms = list()

    def from_json(self, r):
        self.id = int(r['id'])
        self.name = r['name']
        self.short_name = r['short_name']
        self.extra_short_name = r['extra_short_name']

        self.name_en = r['name_en']
        self.short_name_en = r['short_name_en']
        self.wikidata_id = r['wikidata_id']
        self.capital_coords = r['capital_coords']
        self.dative_forms = r.get('dative', list())
        return self


class TRussianRegions:
    Russia_as_s_whole_region_id = 2

    def __init__(self):
        self.regions = list()
        self.max_region_id = 0
        self.region_name_to_region = dict()
        self.region_id_to_region = dict()
        self.capitals_to_regions = dict()
        self.wikidata2region = dict()
        self.all_forms = ahocorasick.Automaton()
        self.nominative_forms = ahocorasick.Automaton()
        self.all_capitals = ahocorasick.Automaton()

        with open(os.path.join(os.path.dirname(__file__), "data", "regions.txt")) as inp:
            regions_json = json.load(inp)
            assert regions_json[0]['id'] == TRussianRegions.Russia_as_s_whole_region_id
            assert len(regions_json) == 85 + 2 # regions + Russia + Baikonur

        for region in regions_json:
            r = TRegion().from_json(region)
            self.regions.append(r)
            self.max_region_id = max(self.max_region_id, r.id)
            self.region_name_to_region[r.name.lower()] = r
            self.region_name_to_region[r.short_name.lower()] = r
            self.region_id_to_region[r.id] = r
            self.wikidata2region[r.wikidata_id] = r

            forms = set([r.name, r.short_name])
            if r.id != TRussianRegions.Russia_as_s_whole_region_id:
                for f in forms:
                    self.nominative_forms.add_word(f.lower(), (r.id, f.lower()))

            for case in ['genitive', 'dative', 'locative']:
                forms.update(region.get(case, []))
            for f in forms:
                self.all_forms.add_word(f.lower(), (r.id, f.lower()))
            if r.id != TRussianRegions.Russia_as_s_whole_region_id:
                capital = normalize_whitespace(region['capital'].lower())
                self.capitals_to_regions[capital] = r
                self.all_capitals.add_word(capital, (r.id, capital))
                if capital.find('ё') != -1:
                    capital = capital.replace("ё", "е")
                    self.capitals_to_regions[capital] = r
                    self.all_capitals.add_word(capital, (r.id, capital))

        self.all_forms.make_automaton()
        self.all_capitals.make_automaton()
        self.nominative_forms.make_automaton()

    def get_region_by_id(self, id: int):
        return self.region_id_to_region[id]

    def iterate_regions_2021(self):
        for r in self.regions:
            if r.id != TRussianRegions.Russia_as_s_whole_region_id and r.id != 102 and r.id != 104 and r.id != 108 and r.id != 111:
                yield r

    def get_region_in_nominative(self, russian_name):
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
        elif russian_name.find(' тыв') != -1:
            return self.region_id_to_region[85]
        elif russian_name.endswith('тыва'):
            return self.region_id_to_region[85]
        elif russian_name.find('карачаево-') != -1:
            return self.region_id_to_region[11]
        elif russian_name.find('северная осетия') != -1:
            return self.region_id_to_region[17]
        elif russian_name.find('чувашская республика') != -1:
            return self.region_id_to_region[91]
        elif russian_name.find('ямало-ненецкий авт.округ') != -1:
            return self.region_id_to_region[104]
        elif russian_name.find('чукотский авт.округ') != -1:
            return self.region_id_to_region[95]
        elif russian_name.find('республика адыгея') != -1:
            return self.region_id_to_region[3]
        elif russian_name.find('татарстан') != -1:
            return self.region_id_to_region[18]
        elif russian_name.find('кузбасс') != -1:
            return self.region_id_to_region[50]
        return self.region_name_to_region.get(russian_name)

    def get_region_in_nominative_and_dative(self, russian_name):
        russian_name = normalize_whitespace(russian_name.strip().lower())
        region: TRegion
        for region in self.regions:
            for region_in_dative in region.dative_forms:
                if russian_name.endswith(region_in_dative):
                    return self.region_id_to_region[region.id]
        return self.get_region_in_nominative(russian_name)

    def get_region_all_forms(self, text, unknown_region=None):
        text = normalize_whitespace(text.strip().lower())
        best_region_id = unknown_region
        max_form_len = 0
        for pos, (region_id, form) in self.all_forms.iter(text):
            if len(form) > max_form_len:
                best_region_id = region_id
                max_form_len = len(form)
        return best_region_id

    def get_region_using_automat(self, automat, text, unknown_region=None):
        text = normalize_whitespace(text.strip().lower().replace(',', ' '))
        for last_pos, (region_id, form) in automat.iter(text):
            start_pos = last_pos + 1 - len(form)
            if start_pos > 0:
                if text[start_pos - 1].isalnum():
                    continue
            if last_pos + 1 < len(text):
                if text[last_pos + 1].isalnum():
                    continue
            return region_id
        return unknown_region

    def search_capital_in_address(self, text, unknown_region=None):
        return self.get_region_using_automat(self.all_capitals, text, unknown_region)

    #nominative in a text
    def search_region_in_address(self, text, unknown_region=None):
        return self.get_region_using_automat(self.nominative_forms, text, unknown_region)

    def calc_region_by_address(self, address):
        region_id = self.search_region_in_address(address)
        if region_id is None:
            region_id = self.search_capital_in_address(address)
        return region_id

    def get_region_by_wikidata_id(self, wikidata_id):
        return self.wikidata2region.get(wikidata_id)

    @staticmethod
    def regions_was_captured_in_2014(region_id):
        return region_id == 109 or region_id == 110


if __name__ == "__main__":
    regions = TRussianRegions()
    for x in sys.stdin:
        region = regions.get_region_in_nominative_and_dative(x)
        if region is None:
            print("{} is not found".format(x.strip()))
        else:
            print("{} -> {}".format(x.strip(), region.name))
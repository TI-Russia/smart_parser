from common.primitives import normalize_whitespace

import json
import os
import sys
import ahocorasick


class TRegion:
    def __init__(self, stats=None):
        self.id = None
        self.name = None
        self.short_name = None
        self.extra_short_name = None
        self.short_name_en = None
        self.name_en = None
        self.name = None
        self.wikidata_id = None
        self.capital_coords = None
        self.capital = None
        self.joined_to = None
        self.dative_forms = list()

        #reference to the last known TRegionYearStats, not serialized here
        self.stats = stats

    def set_stat_data(self, stats):
        self.stats = stats

    @property
    def wikidata_url_html(self):
        if self.wikidata_id is None:
            return ''
        id = self.wikidata_id
        return "<a href=\"https://www.wikidata.org/wiki/{}\">{}</a>".format(id, id)

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
        self.genitive_forms = r.get('genitive', list())
        self.locative_forms = r.get('locative', list())
        self.joined_to = r.get('joined_to')
        self.capital =  r.get('capital')
        return self


class TRussianRegions:
    Russia_as_s_whole_region_id = 2
    Baikonur = 111

    def __init__(self):
        self.regions = list()
        self.max_region_id = 0
        self.region_name_to_region = dict()
        self._region_id_to_region = dict()
        self.capitals_to_regions = dict()
        self.wikidata2region = dict()
        self.all_forms = None
        self.nominative_forms = None
        self.all_capitals = None
        self.read_from_json()
        self._build_all_forms_automaton()
        self._build_automatons_without_russia()

    def read_from_json(self):
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
                self._region_id_to_region[r.id] = r
                self.wikidata2region[r.wikidata_id] = r

    def _build_all_forms_automaton(self):
        #with Russia itself
        self.all_forms = ahocorasick.Automaton()
        r: TRegion
        for r in self.regions:
            forms = set([r.name, r.short_name])
            for cases in [r.genitive_forms, r.dative_forms, r.locative_forms]:
                forms.update(cases)
            if r.id == TRussianRegions.Russia_as_s_whole_region_id:
                forms.add("российская федерация")
            for f in forms:
                self.all_forms.add_word(f.lower(), (r.id, f.lower()))

        self.all_forms.make_automaton()

    def _build_automatons_without_russia(self):
        self.nominative_forms = ahocorasick.Automaton()
        self.all_capitals = ahocorasick.Automaton()
        for r in self.regions:
            if r.id == TRussianRegions.Russia_as_s_whole_region_id:
                continue
            for f in set([r.name, r.short_name]):
                self.nominative_forms.add_word(f.lower(), (r.id, f.lower()))
            capital = normalize_whitespace(r.capital.lower())
            self.capitals_to_regions[capital] = r
            self.all_capitals.add_word(capital, (r.id, capital))
            if capital.find('ё') != -1:
                capital = capital.replace("ё", "е")
                self.capitals_to_regions[capital] = r
                self.all_capitals.add_word(capital, (r.id, capital))
        self.all_capitals.make_automaton()
        self.nominative_forms.make_automaton()

    def get_region_by_id(self, id: int):
        return self._region_id_to_region[id]

    def iterate_inner_regions_without_joined(self):
        for r in self.regions:
            if r.id != TRussianRegions.Russia_as_s_whole_region_id and r.joined_to is None and r.id != TRussianRegions.Baikonur:
                yield r

    def get_region_in_nominative(self, russian_name):
        russian_name = russian_name.lower()
        russian_name = russian_name.replace('респ.', 'республика')
        russian_name = russian_name.replace('сев.', 'северная')
        russian_name = russian_name.replace('авт.', 'автономная')
        if russian_name == "территории за пределами рф":
            return None
        elif russian_name.find('якутия') != -1:
            return self._region_id_to_region[92]
        elif russian_name.find('москва') != -1:
            return self._region_id_to_region[63]
        elif russian_name.find('санкт-петербург') != -1:
            return self._region_id_to_region[1]
        elif russian_name.find('севастополь') != -1:
            return self._region_id_to_region[110]
        elif russian_name.find('ханты') != -1:
            return self._region_id_to_region[108]
        elif russian_name.find('алания') != -1:
            return self._region_id_to_region[17]
        elif russian_name.find(' тыв') != -1:
            return self._region_id_to_region[85]
        elif russian_name.endswith('тыва'):
            return self._region_id_to_region[85]
        elif russian_name.find('карачаево-') != -1:
            return self._region_id_to_region[11]
        elif russian_name.find('северная осетия') != -1:
            return self._region_id_to_region[17]
        elif russian_name.find('чувашская республика') != -1:
            return self._region_id_to_region[91]
        elif russian_name.find('ямало-ненецкий авт.округ') != -1:
            return self._region_id_to_region[104]
        elif russian_name.find('чукотский авт.округ') != -1:
            return self._region_id_to_region[95]
        elif russian_name.find('республика адыгея') != -1:
            return self._region_id_to_region[3]
        elif russian_name.find('татарстан') != -1:
            return self._region_id_to_region[18]
        elif russian_name.find('кузбасс') != -1:
            return self._region_id_to_region[50]
        return self.region_name_to_region.get(russian_name)

    def get_region_in_nominative_and_dative(self, russian_name):
        russian_name = normalize_whitespace(russian_name.strip().lower())
        region: TRegion
        for region in self.regions:
            for region_in_dative in region.dative_forms:
                if russian_name.endswith(region_in_dative):
                    return self._region_id_to_region[region.id]
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

    def get_region_all_forms_at_start(self, text):
        for last_pos, (region_id, form) in self.all_forms.iter(text.lower()):
            start_pos = last_pos + 1 - len(form)
            if start_pos > 0:
                break
            elif start_pos == 0:
                return region_id, start_pos, last_pos + 1
        return None, None, None

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
            return region_id, start_pos, last_pos + 1
        return unknown_region, None, None

    def search_capital_in_address(self, text, unknown_region=None):
        region_id, _, _ = self.get_region_using_automat(self.all_capitals, text, unknown_region)
        return region_id

    #nominative in a text
    def search_region_in_address(self, text, unknown_region=None):
        region_id, _, _ = self.get_region_using_automat(self.nominative_forms, text, unknown_region)
        return region_id

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
    RUSSIAN_REGIONS = TRussianRegions()
    for x in sys.stdin:
        region = RUSSIAN_REGIONS.get_region_in_nominative_and_dative(x)
        if region is None:
            print("{} is not found".format(x.strip()))
        else:
            print("{} -> {}".format(x.strip(), region.name))
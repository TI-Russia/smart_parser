from common.russian_regions import TRussianRegions
from web_site_db.web_sites import TDeclarationWebSiteList

import re
import json
import numpy as np


class TOfficeNgram:
    def __init__(self, ngram_id=None, offices=None):
        self.ngram_id = ngram_id
        self.offices = offices

    def to_json(self):
        rec =  {
            "id": self.ngram_id,
            "offices": self.offices
        }
        return rec

    @staticmethod
    def from_json(js):
        return TOfficeNgram(js['id'], js['offices'])


class TOfficeWebDomain:
    def __init__(self, web_domain_id, offices=None):
        self.web_domain_id = web_domain_id
        self.offices = offices

    def to_json(self):
        rec =  {
            "id": self.web_domain_id,
            "offices": self.offices
        }
        return rec

    @staticmethod
    def from_json(js):
        return TOfficeWebDomain(js['id'], js['offices'])


class TOfficePredictIndex:

    def __init__(self, logger, file_path):
        self.index_file_path = file_path
        self.logger = logger
        self.office_name_bigrams = None
        self.offices = None
        self.web_domains = None
        self.deterministic_web_domains = None
        self.office_id_2_ml_office_id = None
        self.ml_office_id_2_office_id = None
        self.region_words = None
        self.web_sites = TDeclarationWebSiteList(self.logger)
        self.web_sites.load_from_disk()
        self.regions = TRussianRegions()

    def get_bigrams_count(self):
        return len(self.office_name_bigrams)

    def get_web_domain_index(self, web_domain):
        s = self.web_domains.get(web_domain)
        if s is None:
            return 0
        return s.web_domain_id

    def get_offices_by_web_domain(self, web_domain):
        s = self.web_domains.get(web_domain)
        if s is None:
            return list()
        return s.offices

    def get_ml_office_id(self, office_id: int):
        return self.office_id_2_ml_office_id.get(office_id)

    def get_office_id_by_ml_office_id(self, ml_office_id: int):
        return self.ml_office_id_2_office_id.get(ml_office_id)

    def get_bigram_id(self, bigram):
        b = self.office_name_bigrams.get(bigram)
        if b is None:
            return None
        return b.ngram_id

    def get_offices_by_bigram(self, bigram):
        b = self.office_name_bigrams.get(bigram)
        if b is None:
            return list()
        return b.offices

    @staticmethod
    def get_word_stems(text, stem_size=4, add_starter_and_enders=True):
        if add_starter_and_enders:
            yield "^"
        for w in re.split("[\s,\.;:_\"* ()]", text.lower()):
            if len(w) > 0:
                #ignore year
                if w.startswith("20") and len(w) == 4:
                    continue
                if len(w) <= stem_size:
                    yield w
                else:
                    yield w[0:stem_size]
        if add_starter_and_enders:
            yield "$"

    @staticmethod
    def get_bigrams(text):
        words = list(TOfficePredictIndex.get_word_stems(text))
        for w1, w2 in zip(words[:-1], words[1:]):
            yield "_".join((w1, w2))

    @staticmethod
    def get_trigrams(text):
        words = list(TOfficePredictIndex.get_word_stems(text))

        for w1, w2, w3 in zip(words[:-2], words[1:-1], words[2:]):
            yield "_".join((w1, w2, w3))

    def read(self):
        with open(self.index_file_path) as inp:
            js = json.load(inp)
            self.office_name_bigrams = dict((k, TOfficeNgram.from_json(v)) for k, v in js['bigrams'].items())
            self.offices = dict((int(k), v) for k, v in js['offices'].items())
            self.web_domains = dict((k, TOfficeWebDomain.from_json(v)) for k, v in js['web_domains'].items())
            self.deterministic_web_domains = js['deterministic_web_domains']
            self.region_words = js['region_words']
            self.office_id_2_ml_office_id = dict((int(k), v) for k,v in js['office_id_2_ml_office_id'].items())
            self.ml_office_id_2_office_id = dict((int(k), v) for k,v in js['ml_office_id_2_office_id'].items())
        self.logger.info("bigrams count = {}".format(self.get_bigrams_count()))

    def write(self):
        self.logger.info("write to {}".format(self.index_file_path))
        with open(self.index_file_path, "w") as outp:
            rec = {
                'bigrams': dict((k, v.to_json()) for k, v in self.office_name_bigrams.items()),
                'offices': self.offices,
                'web_domains': dict((k, v.to_json()) for k, v in self.web_domains.items()),
                'deterministic_web_domains': self.deterministic_web_domains,
                'region_words': self.region_words,
                'office_id_2_ml_office_id': self.office_id_2_ml_office_id,
                'ml_office_id_2_office_id': self.ml_office_id_2_office_id,
            }
            json.dump(rec, outp, ensure_ascii=False, indent=4)

    def get_office_name(self, office_id: int):
        return self.offices[office_id]['name']

    def get_office_region(self, office_id: int):
        return self.offices[office_id]['region']

    def get_region_from_web_site_title(self, site_url: str):
        site_info = self.web_sites.get_web_site(site_url)
        if site_info is not None and site_info.title is not None:
            return self.regions.get_region_all_forms(site_info.title, 0)
        else:
            return 0

    def get_bigram_feature(self, text: str):
        bigrams_one_hot = np.zeros(self.get_bigrams_count())
        for b in TOfficePredictIndex.get_bigrams(text):
            bigram_id = self.get_bigram_id(b)
            if bigram_id is not None:
                bigrams_one_hot[bigram_id] = 1
        return bigrams_one_hot

    def get_web_site_title_bigram_feature(self, web_domain: str):
        title = self.web_sites.get_title_by_web_domain(web_domain)
        return self.get_bigram_feature(title)



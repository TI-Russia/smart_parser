from common.russian_regions import TRussianRegions
from web_site_db.web_sites import TDeclarationWebSiteList
from common.urllib_parse_pro import urlsplit_pro

import re
import json


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
    def __init__(self, web_domain_id):
        self.web_domain_id = web_domain_id

    def to_json(self):
        rec =  {
            "id": self.web_domain_id,
        }
        return rec

    @staticmethod
    def from_json(js):
        return TOfficeWebDomain(js['id'])


class TOfficePredictIndex:

    def __init__(self, logger, file_path):
        self.index_file_path = file_path
        self.logger = logger
        self.office_name_bigrams = None
        self.office_name_unigrams = None
        self.offices = None
        self.web_domains = None
        self.office_id_2_ml_office_id = None
        self.ml_office_id_2_office_id = None
        self.web_sites = TDeclarationWebSiteList(self.logger)
        self.web_sites.load_from_disk()
        self.regions = TRussianRegions()

    def get_bigrams_count(self):
        return len(self.office_name_bigrams)

    def get_unigrams_count(self):
        return len(self.office_name_unigrams)

    def get_max_region_id(self):
        return self.regions.max_region_id

    def get_web_domain_index(self, web_domain):
        s = self.web_domains.get(web_domain)
        if s is None:
            return 0
        return s.web_domain_id

    def get_web_domains_count(self):
        return len(self.web_domains)

    def get_web_domain_by_url(self, document_url, site_url):
        # first take web domain from which the document was dowloaded
        web_domain = urlsplit_pro(document_url).hostname
        if self.web_sites.get_site_by_web_domain(web_domain) is not None:
            return web_domain
        # if this web domain is unknown, take web domain from site_url
        web_domain = urlsplit_pro(site_url).hostname
        if self.web_sites.get_site_by_web_domain(web_domain) is None:
            self.logger.error("web domain {} is missing in web_sites.json".format(site_url))
        return web_domain

    def get_ml_office_id(self, office_id: int):
        return self.office_id_2_ml_office_id.get(office_id)

    def get_office_id_by_ml_office_id(self, ml_office_id: int):
        return self.ml_office_id_2_office_id.get(ml_office_id)

    def get_bigram_id(self, bigram):
        b = self.office_name_bigrams.get(bigram)
        if b is None:
            return None
        return b.ngram_id

    def get_unigram_id(self, gram):
        b = self.office_name_unigrams.get(gram)
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
        text = text.lower().replace('ё', 'е')
        for word in re.split("[\s,\.;:_\"* ()«»]", text):
            if len(word) == 0:
                continue
            #ignore year
            if word.startswith("20") and len(word) == 4:
                continue
            hyphen_index = word.find('-')
            if hyphen_index > 0:
                if  word[hyphen_index-1] == 'о': #"ямало-ненецкий" не надо разбивать
                    yield word[:stem_size * 2]
                else:
                    w1,w2 = word.split('-', 1)
                    yield w1[:stem_size]  #  split каменск-уральский
                    yield w2[:stem_size]
            else:
                yield word[:stem_size]
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
            self.office_name_unigrams = dict((k, TOfficeNgram.from_json(v)) for k, v in js['unigrams'].items())
            self.offices = dict((int(k), v) for k, v in js['offices'].items())
            self.web_domains = dict((k, TOfficeWebDomain.from_json(v)) for k, v in js['web_domains'].items())
            self.office_id_2_ml_office_id = dict((int(k), v) for k,v in js['office_id_2_ml_office_id'].items())
            self.ml_office_id_2_office_id = dict((int(k), v) for k,v in js['ml_office_id_2_office_id'].items())
        self.logger.info("bigrams count = {}".format(self.get_bigrams_count()))

    def write(self):
        self.logger.info("write to {}".format(self.index_file_path))
        with open(self.index_file_path, "w") as outp:
            rec = {
                'bigrams': dict((k, v.to_json()) for k, v in self.office_name_bigrams.items()),
                'unigrams': dict((k, v.to_json()) for k, v in self.office_name_unigrams.items()),
                'offices': self.offices,
                'web_domains': dict((k, v.to_json()) for k, v in self.web_domains.items()),
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





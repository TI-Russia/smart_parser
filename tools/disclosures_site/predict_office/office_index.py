from common.urllib_parse_pro import TUrlUtf8Encode, urlsplit_pro
from common.russian_regions import TRussianRegions
from web_site_db.web_sites import TDeclarationWebSiteList
from declarations.documents import OFFICES


import re
import json
from django.db import connection
from collections import defaultdict
import numpy as np


def build_web_domain_to_offices():
    sql = """
        (
            select d.office_id, r.web_domain 
            from declarations_source_document d
            join declarations_web_reference r on r.source_document_id = d.id
        )
        union  (
            select d.office_id, r.web_domain 
            from declarations_source_document d
            join declarations_declarator_file_reference r on r.source_document_id = d.id
        )
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        web_domain_to_offices = defaultdict(set)
        for office_id, site_url in cursor:
            if TUrlUtf8Encode.is_idna_string(site_url):
                site_url = TUrlUtf8Encode.convert_url_from_idna(site_url)
            web_domain = urlsplit_pro(site_url).hostname
            web_domain_to_offices[web_domain].add(office_id)
    return web_domain_to_offices


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
        #self.office_name_unigrams = None
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

    #def get_unigrams_count(self):
    #    return len(self.office_name_unigrams)

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

    #def get_unigram_id(self, unigram):
    #    b = self.office_name_unigrams.get(unigram)
    #    if b is None:
    #        return None
    #    return b.ngram_id

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
            #self.office_name_unigrams = dict((k, TOfficeNgram.from_json(v)) for k, v in js['unigrams'].items())
        self.logger.info("bigrams count = {}".format(self.get_bigrams_count()))

    def write(self):
        self.logger.info("write to {}".format(self.index_file_path))
        with open(self.index_file_path, "w") as outp:
            rec = {
                'bigrams': dict((k, v.to_json()) for k, v in self.office_name_bigrams.items()),
                #'unigrams': dict((k, v.to_json()) for k, v in self.office_name_unigrams.items()),
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

    def ngrams_from_default_dict(self, ngrams):
        result = dict()
        for i, b in enumerate(ngrams.keys()):
            ngram_info = TOfficeNgram(i, list(ngrams[b]))
            result[b] = ngram_info
        return result

    def build_name_ngrams(self):
        self.logger.info("build bigrams")
        regions = TRussianRegions()
        office_bigrams = defaultdict(set)
        office_stems = defaultdict(set)
        region_words = set()
        self.offices = dict()
        sql = "select id, name, region_id from declarations_office"
        self.logger.info(sql)
        with connection.cursor() as cursor:
            cursor.execute(sql)
            for office_id, name, region_id in cursor:
                if region_id is None:
                    region_id = 0
                self.offices[office_id] = {
                    'name': name,
                    'region': int(region_id),
                }
                if name.lower().startswith("сведения о"):
                    continue
                for b in self.get_bigrams(name):
                    office_bigrams[b].add(office_id)
                region = regions.get_region_by_id(region_id)
                for w in TOfficePredictIndex.get_word_stems(region.name):
                    region_words.add(w)
                for w in TOfficePredictIndex.get_word_stems(region.short_name):
                    region_words.add(w)
                for w in TOfficePredictIndex.get_word_stems(name, add_starter_and_enders=False):
                    office_stems[w].add(office_id)

        self.office_name_bigrams = self.ngrams_from_default_dict(office_bigrams)
        self.logger.info("bigrams count = {}".format(self.get_bigrams_count()))

        #self.office_name_unigrams = self.ngrams_from_default_dict(office_stems)
        #self.logger.info("unigrams count = {}".format(self.get_unigrams_count()))

        self.region_words = dict((k, i) for (i, k) in enumerate(region_words))

    def build_web_domains(self):
        self.logger.info("build web domains")
        web_domains = build_web_domain_to_offices()
        self.deterministic_web_domains = dict()
        self.web_domains = dict()
        for web_domain, office_ids in web_domains.items():
            self.web_domains[web_domain] = TOfficeWebDomain(len(self.web_domains), list(office_ids))
        self.ml_office_id_2_office_id = dict((i, k) for i,k in enumerate(OFFICES.offices.keys()))
        self.office_id_2_ml_office_id = dict((k, i) for i,k in enumerate(OFFICES.offices.keys()))
        self.logger.info("target office count = {}".format(len(self.office_id_2_ml_office_id)))

    def build(self):
        self.build_name_ngrams()
        self.build_web_domains()

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



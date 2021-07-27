from common.primitives import TUrlUtf8Encode
from common.russian_regions import TRussianRegions

import re
import json
import pymysql
from collections import defaultdict




class TDisclosuresConnection:
    def __init__(self, sql):
        self.connection = None
        self.sql = sql
        self.cursor = None

    def __enter__(self):
        self.connection = pymysql.connect(db="disclosures_db", user="disclosures", password="disclosures")
        self.cursor = self.connection.cursor()
        self.cursor.execute(self.sql)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        self.connection.close()


def build_web_site_to_offices():
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

    with TDisclosuresConnection(sql) as conn:
        website_to_offices = defaultdict(set)
        for office_id, site_url in conn.cursor:
            if TUrlUtf8Encode.is_idna_string(web_domain):
                web_domain = TUrlUtf8Encode.convert_url_from_idna(site_url)
            website_to_offices[web_domain].add(office_id)
    return website_to_offices


class TOfficeIndex:

    def __init__(self, args):
        self.args = args
        self.office_name_bigrams = None
        self.offices = None
        self.web_domains = None
        self.deterministic_web_domains = None
        self.region_words = None

    @staticmethod
    def get_word_stems(text):
        yield "^"
        for w in re.split("[\s,\.;:_\"* ()]", text.lower()):
            if len(w) > 0:
                if w.startswith("20") and len(w) == 4:
                    continue
                # if len(w) <= 2:
                #    continue
                if len(w) <= 3:
                    yield w
                else:
                    yield w[0:3]
        yield "$"

    @staticmethod
    def get_bigrams(text):
        words = list(TOfficeIndex.get_word_stems(text))
        for w1, w2 in zip(words[:-1], words[1:]) :
            yield "_".join((w1, w2))

    @staticmethod
    def get_trigrams(text):
        words = list(TOfficeIndex.get_word_stems(text))

        for w1, w2, w3 in zip(words[:-2], words[1:-1], words[2:]):
            yield "_".join((w1, w2, w3))

    def read(self):
        with open(self.args.bigrams_path) as inp:
            js = json.load(inp)
            self.office_name_bigrams = js['bigrams']
            self.offices = js['offices']
            self.web_domains = js['web_domains']
            self.deterministic_web_domains = js['deterministic_web_domains']
            self.region_words = js['region_words']
        self.args.logger.info("bigrams count = {}".format(len(self.office_name_bigrams)))

    def write(self):
        self.args.logger.info("write to {}".format(self.args.bigrams_path))
        with open(self.args.bigrams_path, "w") as outp:
            rec = {
                'bigrams': self.office_name_bigrams,
                'offices': self.offices,
                'web_domains': self.web_domains,
                'deterministic_web_domains': self.deterministic_web_domains,
                'region_words': self.region_words
            }
            json.dump(rec, outp, ensure_ascii=False, indent=4)

    def get_office_name(self, id):
        return self.offices[str(id)]['name']

    def get_office_region(self, id):
        return self.offices[str(id)]['region']

    def build_bigrams(self):
        self.args.logger.info("build bigrams")
        regions = TRussianRegions()
        office_bigrams = set()
        region_words = set()
        self.offices = dict()
        sql = "select id, name, region_id from declarations_office"
        self.args.logger.info(sql)
        with TDisclosuresConnection(sql) as conn:
            for office_id, name, region_id in conn.cursor:
                if region_id is None:
                    region_id = 0
                self.offices[office_id] = {
                    'name': name,
                    'region': int(region_id),
                }
                if name.lower().startswith("сведения о"):
                    continue
                for b in self.get_bigrams(name):
                    office_bigrams.add(b)
                region = regions.get_region_by_id(region_id)
                for w in TOfficeIndex.get_word_stems(region.name):
                    region_words.add(w)
                for w in TOfficeIndex.get_word_stems(region.short_name):
                    region_words.add(w)
        self.office_name_bigrams = dict((k, i) for (i, k) in enumerate(office_bigrams))
        self.region_words = dict((k, i) for (i, k) in enumerate(region_words))
        self.args.logger.info("bigrams count = {}".format(len(self.office_name_bigrams)))

    def build_web_domains(self):
        self.args.logger.info("build web domains")
        web_domains = build_web_site_to_offices()
        self.deterministic_web_domains = dict()
        self.web_domains = dict()
        for web_domain, office_ids in web_domains.items():
            if len(office_ids) == 1:
                self.deterministic_web_domains[web_domain] = list(office_ids)[0]
            else:
                self.web_domains[web_domain] = len(self.web_domains)

    def build(self):
        self.build_bigrams()
        self.build_web_domains()

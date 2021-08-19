from common.urllib_parse_pro import TUrlUtf8Encode, urlsplit_pro
from disclosures_site.predict_office.office_index import TOfficePredictIndex, TOfficeNgram, TOfficeWebDomain
from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand
from declarations.documents import OFFICES
from collections import defaultdict
from django.db import connection


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


class TOfficePredictIndexBuilder(TOfficePredictIndex):
    def __init(self, logger, file_path):
        super().__init__(logger, file_path)

    def ngrams_from_default_dict(self, ngrams, max_count=-1):
        result = dict()
        for b in ngrams.keys():
            if max_count == -1 or len(ngrams[b]) <= max_count:
                ngram_id = len(result)
                ngram_info = TOfficeNgram(ngram_id, list(ngrams[b]))
                result[b] = ngram_info
        return result

    def build_name_ngrams(self):
        self.logger.info("build bigrams")
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
                region = self.regions.get_region_by_id(region_id)
                for w in TOfficePredictIndex.get_word_stems(region.name):
                    region_words.add(w)
                for w in TOfficePredictIndex.get_word_stems(region.short_name):
                    region_words.add(w)
                for w in TOfficePredictIndex.get_word_stems(name, add_starter_and_enders=False):
                    office_stems[w].add(office_id)

        self.office_name_bigrams = self.ngrams_from_default_dict(office_bigrams)
        self.logger.info("bigrams count = {}".format(self.get_bigrams_count()))

        self.office_name_unigrams = self.ngrams_from_default_dict(office_stems, 3)
        self.logger.info("unigrams count = {}".format(self.get_unigrams_count()))

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


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")

    def handle(self, *args, **options):
        logger = setup_logging(log_file_name="build_office_bigrams.log")
        index = TOfficePredictIndexBuilder(logger, options['bigrams_path'])
        index.build()
        index.write()

from disclosures_site.predict_office.office_index import TOfficePredictIndex, TOfficeNgram, TOfficeWebDomain
from common.logging_wrapper import setup_logging
from django.core.management import BaseCommand
from declarations.documents import OFFICES
from declarations.offices_in_memory import TOfficeInMemory
from collections import defaultdict


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
        self.offices = dict()
        office: TOfficeInMemory
        for office in OFFICES.offices.values():
            region_id = office.region_id
            if region_id is None:
                region_id = 0
            self.offices[office.office_id] = {
                'name': office.name,
                'region': region_id,
                'parent_id': office.parent_id
            }
            for b in self.get_bigrams(office.name):
                office_bigrams[b].add(office.office_id)
            for w in TOfficePredictIndex.get_word_stems(office.name, add_starter_and_enders=False):
                office_stems[w].add(office.office_id)

        self.office_name_bigrams = self.ngrams_from_default_dict(office_bigrams)
        self.logger.info("bigrams count = {}".format(self.get_bigrams_count()))

        self.office_name_unigrams = self.ngrams_from_default_dict(office_stems, 3)
        self.logger.info("unigrams count = {}".format(self.get_unigrams_count()))

    def build_web_domains(self):
        self.web_domains = dict()
        for web_domain in self.web_sites.get_web_domains():
            if  web_domain  is not None:
                for w in TOfficePredictIndex.split_web_domain(web_domain):
                    if w not in self.web_domains:
                        self.web_domains[w] = TOfficeWebDomain(len(self.web_domains))
        self.logger.info("built {} web domains".format(len(self.web_domains)))

    def build_ml_office_indices(self):
        self.ml_office_id_2_office_id = dict((i, k) for i, k in enumerate(OFFICES.offices.keys()))
        self.office_id_2_ml_office_id = dict((k, i) for i, k in enumerate(OFFICES.offices.keys()))
        self.logger.info("target office count = {}".format(len(self.office_id_2_ml_office_id)))

    def build(self):
        self.build_name_ngrams()
        self.build_web_domains()
        self.build_ml_office_indices()


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

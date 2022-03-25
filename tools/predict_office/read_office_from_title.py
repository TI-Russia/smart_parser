from common.russian_morph_dict import TRussianDictWrapper
from common.primitives import normalize_whitespace
from common.decl_title_parser import TDeclarationTitleParser
from office_db.web_site_list import TDeclarationWebSiteList
from office_db.russia import RUSSIA
from predict_office.prediction_case import TPredictionCase
from office_db.offices_in_memory import TDeclarationWebSite


import json

class TOrgNameCompare:
    def __init__(self, office_id,  parser_info: TDeclarationTitleParser):
        self.office_name_in_db = self.normalize_string(RUSSIA.offices_in_memory.get_office_by_id(office_id).name)
        self.org_name = self.normalize_string(parser_info.org_name + " " + " ".join(parser_info.declarant_positions))
        self.parser = parser_info
        self.db_lemmas = set()
        for w in TOrgNameCompare.split_to_tokens(self.office_name_in_db):
            self.db_lemmas.update(l for l, w in TRussianDictWrapper.get_all_lemmas(w))
        self.common_words = set()
        self.weight = 0

    @staticmethod
    def normalize_string(s):
        return normalize_whitespace(s.lower())

    @staticmethod
    def split_to_tokens(org_name):
        words = org_name.lower().strip().split()
        for w in words:
            w = w.strip("\"»«,. ")
            yield w

    def compare(self):
        for w in TOrgNameCompare.split_to_tokens(self.org_name):
            found_lemma = False
            max_word_weight = 1.0
            for l, word_weight in TRussianDictWrapper.get_all_lemmas(w):
                if word_weight > 100:
                    found_lemma = True
                    break
                if word_weight > max_word_weight:
                    max_word_weight = float(word_weight)
                if l in self.db_lemmas:
                    self.common_words.add(l)
                    found_lemma = True
                    self.weight += 1.0 / max_word_weight
                    break
            if not found_lemma and len(w) > 6:
                if self.office_name_in_db.find(w[:6]) != -1:
                    self.common_words.add(w)
                    self.weight += 1.0 / max_word_weight


class TTitleParseResult:
    def __init__(self, office=None, weight=None, org_name=None, common_words=None):
        self.weight = weight
        self.office = office
        self.org_name = org_name
        self.common_words = common_words


class TOfficeFromTitle:
    def __init__(self, logger, web_sites=None):
        self.logger = logger
        if web_sites is not None:
            self.web_sites = web_sites
        else:
            self.web_sites = TDeclarationWebSiteList(logger, RUSSIA.offices_in_memory)

    def parse_title(self, case: TPredictionCase) -> TDeclarationWebSite:
        if case.office_strings is None or len(case.office_strings) == 0:
            return None
        title = json.loads(case.office_strings)['title']
        parser = TDeclarationTitleParser(title)
        if not parser.parse():
            return None
        w = self.web_sites.get_first_site_by_web_domain(case.web_domain)
        if w is None:
            self.logger.error("cannot find url {} in offices.txt".format(case.web_domain))
            return None
        else:
            cmp = TOrgNameCompare(w.parent_office.office_id, parser)
            cmp.compare()
            return TTitleParseResult(w.parent_office, cmp.weight, parser.org_name, cmp.common_words)
        return None

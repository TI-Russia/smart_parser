
from disclosures_site.predict_office.office_pool import TOfficePool
from disclosures_site.predict_office.prediction_case import TPredictionCase
from common.logging_wrapper import setup_logging
from common.decl_title_parser import  TDeclarationTitleParser
from office_db.russia import RUSSIA
from office_db.web_site_list import TDeclarationWebSiteList
from common.russian_morph_dict import TRussianDictWrapper
from common.primitives import normalize_whitespace

import argparse
import json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-pool', dest="input_pool")
    parser.add_argument('--output-toloka-file', dest="output_toloka_file")
    parser.add_argument('--output-automatic-file', dest="output_automatic_file")
    args = parser.parse_args()
    return args

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

def main():
    args = parse_args()
    logger = setup_logging("manage_pool")
    pool = TOfficePool(logger)
    web_sites = TDeclarationWebSiteList(logger, RUSSIA.offices_in_memory)
    pool.read_cases(args.input_pool)
    case: TPredictionCase
    cnt = 0
    toloka_pool = list()
    automatic_pool = list()
    for case in pool.pool:
        cnt += 1
        if case.office_strings is None or len(case.office_strings) == 0:
            continue
        title = json.loads(case.office_strings)['title']
        if len(title) < 5:
            continue
        parser = TDeclarationTitleParser(title)
        #if cnt < 850:
        #    continue
        if not parser.parse():
            logger.debug("cannot parse {}".format(title))
        else:
            #print ("{}".format(json.dumps(parser.to_json(), indent=4, ensure_ascii=False)))
            #print(parser.org_name)
            w = web_sites.get_first_site_by_web_domain(case.web_domain)
            if w is None:
                logger.error("cannot find url {} in offices.txt".format(case.web_domain))
            else:
                cmp = TOrgNameCompare(w.parent_office.office_id, parser)
                cmp.compare()
                if cmp.weight > 0.5:
                    automatic_pool.append(case)
                    case.true_office_id = w.parent_office.office_id
                else:
                    toloka_pool.append(case)
                logger.debug("{}\t{}\t{}\t=>{}:{}".format(w.parent_office.office_id, w.parent_office.name, parser.org_name,
                                              cmp.weight, ",".join(cmp.common_words)))

    TOfficePool.write_pool(toloka_pool, args.output_toloka_file)
    TOfficePool.write_pool(automatic_pool, args.output_automatic_file   )

if __name__ == '__main__':
    main()

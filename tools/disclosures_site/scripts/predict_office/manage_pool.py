
from disclosures_site.predict_office.office_pool import TOfficePool
from disclosures_site.predict_office.prediction_case import TPredictionCase
from common.logging_wrapper import setup_logging
from common.russian_fio import TRussianFio
from common.decl_title_parser import  TDeclarationTitleParser

import argparse
import json
import re


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-pool', dest="input_pool")
    parser.add_argument('--output-file', dest="output_file")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    logger = setup_logging("manage_pool")
    pool = TOfficePool(logger)
    pool.read_cases(args.input_pool)
    c: TPredictionCase
    cnt = 0
    for c in pool.pool:
        cnt += 1
        if c.office_strings is None or len(c.office_strings) == 0:
            continue
        title = json.loads(c.office_strings)['title']
        if len(title) < 5:
            continue
        parser = TDeclarationTitleParser(title)
        if not parser.parse():
            print("cannot parse {}".format(title))
        else:
            print ("{}".format(json.dumps(parser.to_json(), indent=4, ensure_ascii=False)))

        continue

        year = re.search("20[012][0-9]\s*((года)|(г\.))", title)
        if year is not None:
            title = title[:year.start()]
        words = re.split("[»«\"',./:;_{}\[\]()\s]+", title)
        for w in TRussianFio.delete_fios(words):
            if len(w) == 0:
                continue
            if not w[0].isupper():
                continue
            if w[0].isdigit() or w[0] == '№':
                continue
            print(w.title())


if __name__ == '__main__':
    main()

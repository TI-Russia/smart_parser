
from disclosures_site.predict_office.office_pool import TOfficePool
from disclosures_site.predict_office.prediction_case import TPredictionCase
from common.logging_wrapper import setup_logging
from common.russian_fio import TRussianFio
from common.primitives import normalize_whitespace

import argparse
import json
import re



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-pool', dest="input_pool")
    parser.add_argument('--output-file', dest="output_file")
    args = parser.parse_args()
    return args


class TDeclarationTitleParser:
    def __init__(self, title):
        self.title = normalize_whitespace(title)
        self.starter_endpos = None

    def parse(self):
        if not self.find_starter():
            return False
        return True

    def find_starter(self):
        type_regexps = [
            r"^Уточненные Сведения ?о",
            r"^Сведения ?о",
            r"Справка ?о",
            r"Информация ?о"
        ]
        found_type = False
        for r in type_regexps:
            match = re.search(r, self.title, re.IGNORECASE)
            if match is not None:
                offset = match.end()
                found_type = True
                break
        if not found_type:
            return False
        objects_regexps = [
            r"+доходах, *(расходах, *)?об +имуществе +и +обязательствах +имущественного +характера +",
            r"расходах ^(Уточненные )?Сведения о доходах, (расходах, )об имуществе и обязательствах имущественного характера, представленные",
            r"имуществе",
            r"обязательствах имущественного характера",
            ]
        sved =
        for r in regexps:
            match = re.search(r, self.title, re.IGNORECASE )
            if match is not None:
                self.starter_endpos = match.end()
                return True
        return False

def main():
    args = parse_args()
    logger = setup_logging("manage_pool")
    pool = TOfficePool(logger)
    pool.read_cases(args.input_pool)
    c: TPredictionCase
    for c in pool.pool:
        if c.office_strings is None or len(c.office_strings) == 0:
            continue
        title = json.loads(c.office_strings)['title']
        if len(title) < 5:
            continue
        parser = TDeclarationTitleParser(title)
        if not parser.parse():
            print("cannot parse {}".format(title))
        else:
            print("parse starter: success")

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

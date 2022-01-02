from common.russian_fio import TRussianFioRecognizer, TRussianFio
import argparse
import json
from pylem import MorphanHolder, MorphLanguage, LemmaInfo

RUSSIAN_MORPH_DICT = MorphanHolder(MorphLanguage.Russian)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()
    return args


def main1():
    args = parse_args()
    recognizer = TRussianFioRecognizer()

    with open(args.input) as inp:
        for line in inp:
            verdict = "unknown"
            fio = TRussianFio(line.strip(), from_search_request=False, make_lower=False)
            if fio.is_resolved:
                verdict = fio.case
            elif recognizer.string_contains_Russian_name(line):
                verdict = "contain_fio"
            print("{}\t{}".format(line.strip(), verdict))

def main2():
    args = parse_args()
    with open(args.input) as inp:
        for line in inp:
            try:
                f, g = line.strip().split("\t")
                fio = TRussianFio(f, from_search_request=False, make_lower=False)
                if fio.is_resolved and fio.case == "full_name_0":
                    r = {'s': fio.family_name, 'n': fio.first_name, 'p': fio.patronymic, 'g':g}
                    print (json.dumps(r, ensure_ascii=False))
            except ValueError as exp:

                pass


def main3():
    args = parse_args()
    with open(args.input) as inp:
        for line in inp:
            line = line.strip()
            if len(line) == 0 or TRussianFioRecognizer.is_morph_surname_or_predicted(line.strip()):
                continue
            print(line)


if __name__ == "__main__":
    main1()

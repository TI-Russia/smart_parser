from common.russian_fio import TRussianFioRecognizer, TRussianFio
import argparse


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
                if recognizer.is_russian_full_name(fio.family_name, fio.first_name, fio.patronymic):
                    verdict = "full_name"
                else:
                    verdict = "abridged_name"
            elif recognizer.string_contains_Russian_name(line):
                verdict = "contain_fio"
            print("{}\t{}".format(line.strip(), verdict))

def main():
    args = parse_args()
    with open(args.input) as inp:
        for line in inp:
            fio = TRussianFio(line.strip(), from_search_request=False, make_lower=False)
            if fio.is_resolved and fio.case == "full_name_0":
                print ("{}\t{}".format(fio.family_name, fio.first_name+" "+fio.patronymic))


if __name__ == "__main__":
    main()

import argparse
import json
import re
import os
import hashlib
import shutil
import sys
from DeclDocRecognizer.document_types import TCharCategory, SOME_OTHER_DOCUMENTS, VEHICLE_REGEXP_STR, russify, \
        get_russian_normal_text_ratio
from ConvStorage.conversion_client import DECLARATOR_CONV_URL, TDocConversionClient
from DeclDocRecognizer.external_convertors import EXTERNAl_CONVERTORS
from collections import defaultdict

def normalize_whitespace(str):
    str = re.sub(r'\s+', ' ', str)
    str = str.strip()
    return str


class DL_RECOGNIZER_ENUM:
    UNKNOWN = "unknown_result"
    POSITIVE = "declaration_result"
    NEGATIVE = "some_other_document_result"


class FEATURE_ENUM:
    surname_word = "surname_word"
    realty = "realty"
    income = "income"
    transport_word = "transport_word"
    person = "person"
    header = "header"
    other_document_type = "other_document_type"
    vehicles_word = "vehicles_word"
    vehicles = "vehicles"
    relative = "relative"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", dest='source_file', required=True)
    parser.add_argument("--keep-txt", dest='keep_txt', action="store_true", default=False)
    parser.add_argument("--reuse-txt", dest='reuse_txt', action="store_true", default=False)
    parser.add_argument("--output", dest='output', default=None)
    args = parser.parse_args()
    if args.output is None:
        args.output = args.source_file + ".json"
    return args


class TMatch:
    def __init__(self, match_object):
        self.start = match_object.start(0)
        self.end = match_object.end(0)
        self.text = match_object.string[self.start:self.end]

    def to_json(self):
        return {
                "span": "{},{}".format(self.start, self.end),
                "match": self.text
        }



def process_smart_parser_json(json_file):
    with open(json_file, "r", encoding="utf8") as inpf:
        smart_parser_json = json.load(inpf)
        people_count = len(smart_parser_json.get("persons", []))
    os.remove(json_file)
    return people_count


def get_smart_parser_result(source_file):
    global EXTERNAl_CONVERTORS
    global DECLARATOR_CONV_URL
    if source_file.endswith("pdf"):  # cannot process new pdf without conversion
        return 0
    cmd = "{} -converted-storage-url {} -skip-relative-orphan -skip-logging -adapter prod -fio-only {}".format(
        EXTERNAl_CONVERTORS.smart_parser,
        DECLARATOR_CONV_URL,
        source_file)
    os.system(cmd)

    json_file = source_file + ".json"
    if os.path.exists(json_file):
        people_count = process_smart_parser_json(json_file)
    else:
        sheet_index = 0
        people_count = 0
        while True:
            json_file = "{}_{}.json".format(source_file, sheet_index)
            if not os.path.exists(json_file):
                break
            people_count += process_smart_parser_json(json_file)
            sheet_index += 1
    return people_count

class TTextFeature:
    def __init__(self):
        self.first_matches = dict()
        self.all_matches_count = 0

    def to_json(self):
        return {
            "first_matches" :  list(m.to_json() for m in self.first_matches.values()),
            "all_matches_count": self.all_matches_count
        }

class TClassificationVerdict:

    def __init__(self, input_text, smart_parser_person_count):
        self.verdict = DL_RECOGNIZER_ENUM.UNKNOWN
        self.smart_parser_person_count = smart_parser_person_count
        input_text = normalize_whitespace(input_text)
        self.start_text = input_text[0:500]
        self.input_text = input_text
        self.text_features = defaultdict(TTextFeature)
        self.description = ""
        self.normal_russian_text_coef = get_russian_normal_text_ratio(self.input_text)
        self.find_other_document_types()
        self.find_header()

    def to_json(self):
        rec = {
            "verdict": self.verdict,
            "smart_parser_person_count": self.smart_parser_person_count,
            "start_text": self.start_text,
            "text_len": len(self.input_text),
            "description": self.description,
            "normal_russian_text_coef": self.normal_russian_text_coef,
            "text_features": dict((k, v.to_json()) for k, v in self.text_features.items()),
        }
        return rec

    def add_matches(self, match_object, feature_name, max_count=10):
        if match_object is None:
            return False
        cnt = 0
        matches = list(match_object)
        if len(matches) == 0:
            return False
        self.text_features[feature_name].all_matches_count += len(matches)
        for x in matches[:max_count]:
            m = TMatch(x)
            self.text_features[feature_name].first_matches[m.start] = m
            cnt += 1
        return cnt > 0

    def get_first_features_match(self, feature_name):
        f = self.text_features.get(feature_name)
        if f is None:
            return sys.maxsize
        if len(f.first_matches) == 0:
            return sys.maxsize
        return min(f.first_matches.keys())

    def get_features_match_count(self, feature_name):
        x = self.text_features.get(feature_name)
        if x is None:
            return 0
        return x.all_matches_count

    def find_person(self):
        regexp = "[А-Я]\w+ [А-Я]\w+ [А-Я]\w+((вич)|(ьич)|(кич)|(вна)|(чна))"  # # Сокирко Алексей Викторович
        if self.add_matches(re.finditer(regexp, self.input_text), FEATURE_ENUM.person):
            pass
        else:
            regexp = "[А-Я]\w+ [А-Я]\. *[А-Я]\."  # Сокирко А.В.
            self.add_matches(re.finditer(regexp, self.input_text), FEATURE_ENUM.person)

    def find_relatives(self):
        regexp = "супруга|(несовершеннолетний ребенок)|сын|дочь|(супруг\b)"
        self.add_matches(re.finditer(regexp, self.input_text), FEATURE_ENUM.relative)

    def find_vehicles(self):
        global VEHICLE_REGEXP_STR
        self.add_matches(re.finditer(VEHICLE_REGEXP_STR, self.input_text, re.IGNORECASE), FEATURE_ENUM.vehicles)

        input_text = russify(self.input_text).lower()
        self.add_matches(re.finditer(VEHICLE_REGEXP_STR, input_text, re.IGNORECASE), FEATURE_ENUM.vehicles)

    def find_vehicles_word(self):
        regexp = "транспорт|транспортных"
        self.add_matches(re.finditer(regexp, self.input_text, re.IGNORECASE), FEATURE_ENUM.vehicles_word)

    def find_income(self):
        regexp = '[0-9]{6}'
        self.add_matches(re.finditer(regexp, self.input_text.replace(' ', ''), re.IGNORECASE), FEATURE_ENUM.income)

    def find_realty(self):
        estates = ["квартира", "земельный участок", "жилое помещение", "комната", "долевая", "з/ *участок", "ж/ *дом",
                   "жилой дом", "машиноместо", "гараж", "приусадебный участок"]
        regexp = "|".join(map((lambda x: "({})".format(x)), estates))
        self.add_matches(re.finditer(regexp, self.input_text, re.IGNORECASE), FEATURE_ENUM.realty)

    def find_surname_word(self):
        regexp = "(фамилия)|(фио)|(ф.и.о.)"
        self.add_matches(re.finditer(regexp, self.input_text, re.IGNORECASE), FEATURE_ENUM.surname_word)

    def find_header(self):
        input_text = russify(self.input_text).lower()
        regexps = [
            r"(Сведения о доходах)",
            r"(Сведения о расходах)",
            r"(Сведения об имущественном положении и доходах)",
            r"((Фамилия|ФИО).{1,200}Должность.{1,200}Перечень объектов.{1,200}транспортных)",
            r"(Сведения *,? предоставленные руководителями)",
            r"(Перечень объектов недвижимого имущества ?, принадлежащих)",
            r"(Сведения об источниках получения средств)",
            r"(декларированный доход)",
        ]

        regexp = '(' + "|".join(regexps) + ")"
        self.add_matches(re.finditer(regexp, input_text, re.IGNORECASE), FEATURE_ENUM.header)

    def find_other_document_types(self):
        global SOME_OTHER_DOCUMENTS
        words = list()
        for w in SOME_OTHER_DOCUMENTS:
            words.append('(' + " *".join(w) + ')')
        regexp = '(' + "|".join(words) + ")" + r"\b"
        self.add_matches(re.finditer(regexp, self.input_text, re.IGNORECASE), FEATURE_ENUM.other_document_type)


def read_input_text(filename):
    with open(filename, "r", encoding="utf8", errors="ignore") as inpf:
        input_text = inpf.read().replace("\n", " ").replace("\r", " ").replace('"', ' ').strip("\t \n\r")
        input_text = input_text.replace('*', '')  # footnotes
        input_text = ' '.join(input_text.split())
        return input_text


def initialize_classification_vedict(source_file, input_text):
    verdict = TClassificationVerdict(input_text, get_smart_parser_result(source_file))
    return verdict


def apply_first_rules(source_file, verdict):
    _, file_extension = os.path.splitext(source_file)
    if len(verdict.input_text) < 200:
        if file_extension in {".html", ".htm", ".docx", ".doc", ".xls", ".xlsx"}:
            if len(verdict.input_text) == 0:
                verdict.description = "file is too short"  # jpeg in document
            else:
                verdict.verdict = DL_RECOGNIZER_ENUM.NEGATIVE  # fast empty files, but not empty
                verdict.description = "file is too short"  # jpeg in document
        else:
            verdict.description = "file is too short"
    elif verdict.get_first_features_match("header") < 20:
        verdict.verdict = DL_RECOGNIZER_ENUM.POSITIVE
        verdict.description = "header < 20"
    elif verdict.get_first_features_match('other_document_type') == 0:
        verdict.verdict = DL_RECOGNIZER_ENUM.NEGATIVE
        verdict.description = "other_document_type=0"
    elif TCharCategory.get_most_popular_char_category(verdict.start_text) != 'RUSSIAN_CHAR':
        verdict.verdict = DL_RECOGNIZER_ENUM.UNKNOWN
        verdict.description = "cannot find Russian chars, may be encoding problems"
    elif file_extension not in {".html", ".htm"} and verdict.get_first_features_match('other_document_type') < 400:
        verdict.verdict = DL_RECOGNIZER_ENUM.NEGATIVE
        verdict.description = "other_document_type<400"
    elif verdict.smart_parser_person_count > 0 and len(verdict.input_text) / verdict.smart_parser_person_count < 2048:
        verdict.verdict = DL_RECOGNIZER_ENUM.POSITIVE
        verdict.description = "found smart_parser results"
    elif verdict.normal_russian_text_coef > 0.19:
        verdict.verdict = DL_RECOGNIZER_ENUM.NEGATIVE
        verdict.description = "normal_russian_text_coef > 0.19"
    else:
        return False
    return True


def apply_second_rules(verdict):
    verdict.find_person()
    verdict.find_relatives()
    verdict.find_vehicles()
    verdict.find_vehicles_word()
    verdict.find_income()
    verdict.find_realty()
    verdict.find_surname_word()
    person_count = verdict.get_features_match_count(FEATURE_ENUM.person)
    realty_count = verdict.get_features_match_count(FEATURE_ENUM.realty)
    vehicle_count = verdict.get_features_match_count(FEATURE_ENUM.vehicles)
    header_count = verdict.get_features_match_count(FEATURE_ENUM.header)
    verdict.verdict = DL_RECOGNIZER_ENUM.NEGATIVE
    if float(vehicle_count)/float(len(verdict.input_text)) > 0.0001 and verdict.get_features_match_count(FEATURE_ENUM.surname_word) > 0:
        verdict.verdict = DL_RECOGNIZER_ENUM.POSITIVE
        verdict.description = "enough vehicles and surnames_word"
    elif verdict.get_first_features_match(FEATURE_ENUM.surname_word) == 0 and len(verdict.input_text) < 2000 \
            and person_count > 0 and realty_count > 0:
        verdict.verdict = DL_RECOGNIZER_ENUM.POSITIVE
        verdict.description = "person name is at start and realty_count > 0"
    elif header_count > 0:
        if realty_count > 5:
            verdict.verdict = DL_RECOGNIZER_ENUM.POSITIVE
            verdict.description = "header is found and realty_count > 5"
        elif person_count > 2 and verdict.get_first_features_match(FEATURE_ENUM.header) < verdict.get_first_features_match(FEATURE_ENUM.person):
            verdict.verdict = DL_RECOGNIZER_ENUM.POSITIVE
            verdict.description = "person_count > 2  and header is before person"
        elif person_count > 0 and realty_count > 0:
            verdict.verdict = DL_RECOGNIZER_ENUM.POSITIVE
            verdict.description = "header found and person_count > 0  and realties are found"
        elif vehicle_count > 0 and verdict.get_features_match_count(FEATURE_ENUM.surname_word) > 0:
            verdict.verdict = DL_RECOGNIZER_ENUM.POSITIVE
            verdict.description = "headers and vehicles and surnames_word"


def external_convert(source_file, reuse_txt=False):
    global EXTERNAl_CONVERTORS
    ec = EXTERNAl_CONVERTORS
    _, file_extension = os.path.splitext(source_file)
    file_extension = file_extension.lower()
    txt_file = source_file + ".txt"
    if reuse_txt and os.path.exists(txt_file):
        return txt_file
    if file_extension == ".xlsx":
        ec.run_xlsx2csv(source_file, txt_file)
    elif file_extension == ".xls":
        res = ec.run_xls2csv(source_file, txt_file)
        if res != 0:
            temp_fname = source_file + ".xlsx"
            shutil.copy(source_file, temp_fname)
            ec.run_xlsx2csv(temp_fname, txt_file)
            os.unlink(temp_fname)
    elif file_extension == ".docx":
        ec.run_office2txt(source_file, txt_file)
    elif file_extension == ".pdf":
        temp_file = source_file + ".docx"
        with open(source_file, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
            if TDocConversionClient().retrieve_document(sha256, temp_file):
                ec.run_office2txt(temp_file, txt_file)
            else:
                # the worse case, let's use calibre
                ec.run_calibre(source_file, txt_file)
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    elif file_extension in {".html", ".rtf", ".htm"}:
        ec.run_calibre(source_file, txt_file)
    elif file_extension == ".doc":
        res = ec.run_catdoc(source_file, txt_file)
        if res != 0:
            temp_fname = source_file + ".docx"
            shutil.copy(source_file, temp_fname)
            ec.run_office2txt(temp_fname, txt_file)
            os.unlink(temp_fname)
    else:
        ec.run_soffice(source_file, txt_file)
    return txt_file


def get_classification_verdict(source_file, txt_file):
    if not os.path.exists(txt_file):
        v = TClassificationVerdict("", 0)
        v.verdict = DL_RECOGNIZER_ENUM.NEGATIVE
        v.description = "cannot parse document"
        return v
    else:
        input_text = read_input_text(txt_file)
        verdict = initialize_classification_vedict(source_file, input_text)
        if not apply_first_rules(source_file, verdict):
            apply_second_rules(verdict)
        return verdict


def run_dl_recognizer(source_file, keep_txt=False, reuse_txt=False):
    txt_file = external_convert(source_file, reuse_txt)
    verdict = get_classification_verdict(source_file, txt_file)
    if not keep_txt and os.path.exists(txt_file):
        os.unlink(txt_file)
    return verdict


if __name__ == "__main__":
    args = parse_args()
    verdict = run_dl_recognizer(args.source_file, args.keep_txt, args.reuse_txt)
    with open(args.output, "w", encoding="utf8") as outf:
        outf.write(json.dumps(verdict.to_json(), ensure_ascii=False, indent=4))

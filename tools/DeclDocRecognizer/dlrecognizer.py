from DeclDocRecognizer.document_types import TCharCategory, SOME_OTHER_DOCUMENTS, VEHICLE_REGEXP_STR, russify, \
        get_russian_normal_text_ratio
from ConvStorage.conversion_client import TDocConversionClient
from DeclDocRecognizer.external_convertors import EXTERNAl_CONVERTORS
from common.primitives import normalize_whitespace, string_contains_Russian_name


from collections import defaultdict
import argparse
import json
import re
import os
import hashlib
import shutil
import sys


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
    other_document_type_smart_parser_title = "other_document_type_smart_parser_title"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", dest='source_file', required=True)
    parser.add_argument("--keep-txt", dest='keep_txt', action="store_true", default=False)
    parser.add_argument("--reuse-txt", dest='reuse_txt', action="store_true", default=False)
    parser.add_argument("--output-verdict", dest='output_verdict', default=None)
    parser.add_argument("--delete-negative", dest='delete_negative', default=False, action="store_true")
    parser.add_argument("--output-folder", dest='output_folder', default=None,
                        help="save all temp files to this folder")
    args = parser.parse_args()
    if args.output_folder is not None:
        os.makedirs(args.output_folder, exist_ok=True)
    if args.output_verdict is None:
        if args.output_folder is None:
            args.output_verdict = args.source_file + ".verdict"
        else:
            args.output_verdict = os.path.join(args.output_folder,  os.path.basename(args.source_file) + ".verdict")
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


def get_smart_parser_result(source_file):
    if source_file.endswith("pdf"):  # cannot process new pdf without conversion
        return 0, ""
    EXTERNAl_CONVERTORS.run_smart_parser_short(source_file)
    json_file = source_file + ".json"
    if not os.path.exists(json_file):
        return 0, ""
    with open(json_file, "r", encoding="utf8") as inpf:
        smart_parser_json = json.load(inpf)
    os.remove(json_file)
    good_names_count = 0
    bad_names_count = 0
    for p in smart_parser_json.get("persons", []):
        name = p.get('person', {}).get('name_raw','')
        if string_contains_Russian_name(name):
            good_names_count += 1
        else:
            bad_names_count += 1
    #good_names_ratio = good_names_count*5 > (good_names_count + bad_names_count)
    #number_of_persons = len(smart_parser_json.get("persons", []))
    if good_names_count*5 < (good_names_count + bad_names_count):
        good_names_count = 0
    number_of_persons = good_names_count
    return number_of_persons, smart_parser_json.get('document', {}).get("sheet_title", "")


class TTextFeature:
    def __init__(self):
        self.first_matches = dict()
        self.all_matches_count = 0

    def to_json(self):
        return {
            "first_matches" :  list(m.to_json() for m in self.first_matches.values()),
            "all_matches_count": self.all_matches_count
        }


SOME_OTHER_DOCUMENTS_REGEXP = '(' + "|".join(list('(' + " *".join(w) + ')' for w in SOME_OTHER_DOCUMENTS)) + ")" + r"\b"


class TClassificationVerdict:

    def __init__(self, source_file, input_text):
        self.source_file = source_file
        self.verdict = DL_RECOGNIZER_ENUM.UNKNOWN
        if self.source_file is not None:
            self.smart_parser_person_count, self.smart_parser_title = get_smart_parser_result(self.source_file)
        else:
            self.smart_parser_person_count, self.smart_parser_title = 0, ""
        input_text = normalize_whitespace(input_text)
        self.start_text = input_text[0:500]
        self.input_text = input_text
        self.text_features = defaultdict(TTextFeature)
        self.description = ""
        self.normal_russian_text_coef = get_russian_normal_text_ratio(self.input_text)
        self.find_other_document_types()
        self.find_header()
        self.find_other_document_types_in_smart_parser_title()

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
        self.add_matches(re.finditer(SOME_OTHER_DOCUMENTS_REGEXP,
                                     self.input_text, re.IGNORECASE),
                                    FEATURE_ENUM.other_document_type)

    def find_other_document_types_in_smart_parser_title(self):
        self.add_matches(re.finditer(SOME_OTHER_DOCUMENTS_REGEXP,
                                     self.smart_parser_title, re.IGNORECASE),
                                    FEATURE_ENUM.other_document_type_smart_parser_title)

    def apply_first_rules(self):
        _, file_extension = os.path.splitext(self.source_file)
        if len(self.input_text) < 200:
            if file_extension in {".html", ".htm", ".docx", ".doc", ".xls", ".xlsx"}:
                if len(self.input_text) == 0:
                    self.description = "file is too short"  # jpeg in document
                else:
                    self.verdict = DL_RECOGNIZER_ENUM.NEGATIVE  # fast empty files, but not empty
                    self.description = "file is too short"  # jpeg in document
            else:
                self.description = "file is too short"
        elif self.get_first_features_match("header") < 20:
            self.verdict = DL_RECOGNIZER_ENUM.POSITIVE
            self.description = "header < 20"
        elif self.get_first_features_match('other_document_type') == 0:
            self.verdict = DL_RECOGNIZER_ENUM.NEGATIVE
            self.description = "other_document_type=0"
        elif self.get_first_features_match('other_document_type_smart_parser_title') == 0:
            self.verdict = DL_RECOGNIZER_ENUM.NEGATIVE
            self.description = "other_document_type_smart_parser_title=0"
        elif TCharCategory.get_most_popular_char_category(self.start_text) != 'RUSSIAN_CHAR':
            self.verdict = DL_RECOGNIZER_ENUM.UNKNOWN
            self.description = "cannot find Russian chars, may be encoding problems"
        elif file_extension not in {".html", ".htm"} and self.get_first_features_match('other_document_type') < 400:
            self.verdict = DL_RECOGNIZER_ENUM.NEGATIVE
            self.description = "other_document_type<400"
        elif self.smart_parser_person_count > 0 and len(self.input_text) / self.smart_parser_person_count < 2048:
            self.verdict = DL_RECOGNIZER_ENUM.POSITIVE
            self.description = "found smart_parser results"
        elif self.normal_russian_text_coef > 0.19:
            self.verdict = DL_RECOGNIZER_ENUM.NEGATIVE
            self.description = "normal_russian_text_coef > 0.19"
        else:
            return False
        return True

    def apply_second_rules(self):
        self.find_person()
        self.find_relatives()
        self.find_vehicles()
        self.find_vehicles_word()
        self.find_income()
        self.find_realty()
        self.find_surname_word()
        person_count = self.get_features_match_count(FEATURE_ENUM.person)
        realty_count = self.get_features_match_count(FEATURE_ENUM.realty)
        vehicle_count = self.get_features_match_count(FEATURE_ENUM.vehicles)
        header_count = self.get_features_match_count(FEATURE_ENUM.header)
        self.verdict = DL_RECOGNIZER_ENUM.NEGATIVE
        if float(vehicle_count)/float(len(self.input_text)) > 0.0001 and self.get_features_match_count(FEATURE_ENUM.surname_word) > 0:
            self.verdict = DL_RECOGNIZER_ENUM.POSITIVE
            self.description = "enough vehicles and surnames_word"
        elif self.get_first_features_match(FEATURE_ENUM.surname_word) == 0 and len(self.input_text) < 2000 \
                and person_count > 0 and realty_count > 0:
            self.verdict = DL_RECOGNIZER_ENUM.POSITIVE
            self.description = "person name is at start and realty_count > 0"
        elif header_count > 0:
            if realty_count > 5:
                self.verdict = DL_RECOGNIZER_ENUM.POSITIVE
                self.description = "header is found and realty_count > 5"
            elif person_count > 2 and self.get_first_features_match(FEATURE_ENUM.header) < self.get_first_features_match(FEATURE_ENUM.person):
                self.verdict = DL_RECOGNIZER_ENUM.POSITIVE
                self.description = "person_count > 2  and header is before person"
            elif person_count > 0 and realty_count > 0:
                self.verdict = DL_RECOGNIZER_ENUM.POSITIVE
                self.description = "header found and person_count > 0  and realties are found"
            elif vehicle_count > 0 and self.get_features_match_count(FEATURE_ENUM.surname_word) > 0:
                self.verdict = DL_RECOGNIZER_ENUM.POSITIVE
                self.description = "headers and vehicles and surnames_word"


def read_input_text(filename):
    with open(filename, "r", encoding="utf8", errors="ignore") as inpf:
        input_text = inpf.read().replace("\n", " ").replace("\r", " ").replace('"', ' ').strip("\t \n\r")
        input_text = input_text.replace('*', '')  # footnotes
        input_text = ' '.join(input_text.split())
        return input_text


def get_text_of_a_document(source_file, keep_txt=False, reuse_txt=False, output_folder=None):
    global EXTERNAl_CONVERTORS
    ec = EXTERNAl_CONVERTORS
    _, file_extension = os.path.splitext(source_file)
    file_extension = file_extension.lower()
    if output_folder is None:
        txt_file = source_file + ".txt"
    else:
        txt_file = os.path.join(output_folder, os.path.basename(source_file) + ".txt")

    if reuse_txt and os.path.exists(txt_file):
        pass
    elif file_extension == ".xlsx":
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
        return None
    if os.path.exists(txt_file):
        doc_text = read_input_text(txt_file)
        if not keep_txt:
            os.unlink(txt_file)
        return doc_text
    else:
        return None


def run_dl_recognizer(source_file, keep_txt=False, reuse_txt=False, output_folder=None):
    input_text = get_text_of_a_document(source_file, keep_txt, reuse_txt, output_folder)
    if input_text is None:
        v = TClassificationVerdict(None, "")
        v.verdict = DL_RECOGNIZER_ENUM.NEGATIVE
        v.description = "cannot parse document"
        return v
    else:
        verdict = TClassificationVerdict(source_file, input_text)
        if not verdict.apply_first_rules():
            verdict.apply_second_rules()
        return verdict
    return verdict


if __name__ == "__main__":
    args = parse_args()
    verdict = run_dl_recognizer(args.source_file, args.keep_txt, args.reuse_txt, args.output_folder)
    if args.delete_negative:
        if verdict.verdict == DL_RECOGNIZER_ENUM.NEGATIVE:
            os.unlink(args.source_file)
    else:
        with open(args.output_verdict, "w", encoding="utf8") as outf:
            outf.write(json.dumps(verdict.to_json(), ensure_ascii=False, indent=4))

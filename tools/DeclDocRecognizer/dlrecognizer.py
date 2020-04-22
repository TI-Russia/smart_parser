import argparse
import json
import re
import os
import hashlib
import shutil
import sys
from DeclDocRecognizer.document_types import TCharCategory, SOME_OTHER_DOCUMENTS, VEHICLE_REGEXP_STR, russify
from ConvStorage.conversion_client import DECLARATOR_CONV_URL, TConversionTasks
from DeclDocRecognizer.external_convertors import EXTERNAl_CONVERTORS


class DL_RECOGNIZER_ENUM:
    UNKNOWN = "unknown_result"
    POSITIVE = "declaration_result"
    NEGATIVE = "some_other_document_result"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", dest='source_file', required=True)
    parser.add_argument("--keep-temp", dest='keep_temp', action="store_true", default=False)
    parser.add_argument("--output", dest='output', default=None)
    args = parser.parse_args()
    if args.output is None:
        args.output = args.source_file + ".json"
    return args


def get_matches(match_object, result, name, max_count=10):
    if match_object is None:
        return False
    matches = list()
    first_offset = -1
    for x in match_object:
        if first_offset == -1:
            first_offset = x.start()
        matches.append(str(x))
        if len(matches) >= max_count:
            result[name] = {
                'matches': matches,
                "start": first_offset
            }
            break
    if len(matches) == 0:
        return False
    result[name] = {
        'matches': matches,
        "start": first_offset
    }
    return True


def find_person(input_text, result, name):
    regexp = "[А-Я]\w+ [А-Я]\w+ [А-Я]\w+((вич)|(ьич)|(кич)|(вна)|(чна))"  # # Сокирко Алексей Викторович
    if get_matches(re.finditer(regexp, input_text), result, name):
        pass
    else:
        regexp = "[А-Я]\w+ [А-Я]\. *[А-Я]\."  # Сокирко А.В.
        get_matches(re.finditer(regexp, input_text), result, name)


def find_relatives(input_text, result, name):
    regexp = "супруга|(несовершеннолетний ребенок)|сын|дочь|(супруг\b)"
    get_matches(re.finditer(regexp, input_text), result, name)


def find_vehicles(input_text, result, name):
    global VEHICLE_REGEXP_STR
    input_text = russify(input_text).lower()
    get_matches(re.finditer(VEHICLE_REGEXP_STR, input_text, re.IGNORECASE), result, name)


def find_vehicles_word(input_text, result, name):
    regexp = "транспорт|транспортных"
    get_matches(re.finditer(regexp, input_text, re.IGNORECASE), result, name)


def find_income(input_text, result, name):
    regexp = '[0-9]{6}'
    get_matches(re.finditer(regexp, input_text.replace(' ', ''), re.IGNORECASE), result, name)


def find_realty(input_text, result, name):
    estates = ["квартира", "земельный участок", "жилое помещение", "комната", "долевая", "з/ *участок", "ж/ *дом",
               "жилой дом", "машиноместо", "гараж", "приусадебный участок"]
    regexp = "|".join(map((lambda x: "({})".format(x)), estates) )
    get_matches(re.finditer(regexp, input_text, re.IGNORECASE), result, name)


def find_suname_word(input_text, result, name):
    regexp = "(фамилия)|(фио)|(ф.и.о.)"
    get_matches(re.finditer(regexp, input_text, re.IGNORECASE), result, name)


def find_header(input_text, result, name):
    input_text = russify(input_text).lower()
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
    get_matches(re.finditer(regexp, input_text, re.IGNORECASE), result, name)


def find_other_document_types(input_text, result, name):
    global SOME_OTHER_DOCUMENTS
    words = list()
    for w in SOME_OTHER_DOCUMENTS:
        words.append('(' + " *".join(w) + ')')
    regexp = '(' + "|".join(words) + ")" + r"\b"
    get_matches(re.finditer(regexp, input_text, re.IGNORECASE), result, name)


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


def read_input_text(filename):
    with open(filename, "r", encoding="utf8", errors="ignore") as inpf:
        input_text = inpf.read().replace("\n", " ").replace("\r", " ").replace('"', ' ').strip("\t \n\r")
        input_text = input_text.replace('*', '')  # footnotes
        input_text = ' '.join(input_text.split())
        return input_text


def initialize_classification_vedict(source_file, input_text):
    verdict = { "result": DL_RECOGNIZER_ENUM.UNKNOWN,
                "smart_parser_person_count": get_smart_parser_result(source_file)
              }
    verdict["start_text"] = input_text[0:500]
    verdict["text_len"] = len(input_text)
    find_other_document_types(input_text, verdict, "other_document_type")
    find_header(input_text, verdict, "header")
    return verdict


def apply_first_rules(source_file, verdict, input_text):
    _, file_extension = os.path.splitext(source_file)
    if len(input_text) < 200:
        if file_extension in {".html", ".htm", ".docx", ".doc", ".xls", ".xlsx"}:
            if len(input_text) == 0:
                verdict["description"] = "file is too short"  # jpeg in document
            else:
                verdict["result"] = DL_RECOGNIZER_ENUM.NEGATIVE  # fast empty files, but not empty
        else:
            verdict["description"] = "file is too short"
    elif verdict.get("header", dict()).get("start", 21) < 20:
        verdict["result"] = DL_RECOGNIZER_ENUM.POSITIVE
    elif verdict.get('other_document_type', {}).get("start", sys.maxsize) == 0:
        verdict["result"] = DL_RECOGNIZER_ENUM.NEGATIVE
    elif TCharCategory.get_most_popular_char_category(verdict["start_text"]) != 'RUSSIAN_CHAR':
        verdict["result"] = DL_RECOGNIZER_ENUM.UNKNOWN
        verdict["description"] = "cannot find Russian chars, may be encoding problems"
    elif verdict.get('other_document_type', {}).get("start", sys.maxsize) < 400:
        verdict["result"] = DL_RECOGNIZER_ENUM.NEGATIVE
    elif verdict['smart_parser_person_count'] > 0 and len(input_text) / verdict['smart_parser_person_count'] < 2048:
        verdict["result"] = DL_RECOGNIZER_ENUM.POSITIVE
    else:
        return False
    return True


def apply_second_rules(verdict, input_text):
    find_person(input_text, verdict, "person")
    find_relatives(input_text, verdict, "relative")  # not used
    find_vehicles(input_text, verdict, "auto")
    find_vehicles_word(input_text, verdict, "transport_word")
    find_income(input_text, verdict, "income")  # not used
    find_realty(input_text, verdict, "realty")
    find_suname_word(input_text, verdict, "surname_word")
    person_count = len(verdict.get('person', dict()).get('matches', list()))
    #relative_count = len(verdict.get('relative', dict()).get('matches', list()))
    realty_count = len(verdict.get('realty', dict()).get('matches', list()))
    vehicle_count = len(verdict.get('auto', dict()).get('matches', list()))
    is_declaration = False
    if vehicle_count > 0 and verdict.get("surname_word") is not None:
        is_declaration = True
    elif verdict.get("surname_word", dict()).get("start", 1) == 0 and len(
            input_text) < 2000 and person_count > 0 and realty_count > 0:
        is_declaration = True
    elif realty_count > 5 and verdict.get("header") is not None:
        is_declaration = True
    elif person_count > 0 and verdict.get("header") is not None:
        if person_count > 2 and verdict["header"]['start'] < verdict["person"]['start']:
            is_declaration = True
        else:
            if realty_count > 0:
                is_declaration = True

    verdict["result"] = DL_RECOGNIZER_ENUM.POSITIVE if is_declaration else DL_RECOGNIZER_ENUM.NEGATIVE


def external_convert(source_file):
    global EXTERNAl_CONVERTORS
    ec = EXTERNAl_CONVERTORS
    _, file_extension = os.path.splitext(source_file)
    file_extension = file_extension.lower()
    txt_file = source_file + ".txt"
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
            if TConversionTasks().retrieve_document(sha256, temp_file):
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
        return {
            "result": DL_RECOGNIZER_ENUM.NEGATIVE,
            "description": "cannot parse document"
        }
    else:
        input_text = read_input_text(txt_file)
        verdict = initialize_classification_vedict(source_file, input_text)
        if not apply_first_rules(source_file, verdict, input_text):
            apply_second_rules(verdict, input_text)
        return verdict


def run_dl_recognizer(source_file, keep_temp=False):
    txt_file = external_convert(source_file)
    verdict = get_classification_verdict(source_file, txt_file)
    if not keep_temp and os.path.exists(txt_file):
        os.unlink(txt_file)
    return verdict


if __name__ == "__main__":
    args = parse_args()
    verdict = run_dl_recognizer(args.source_file, args.keep_temp)
    with open(args.output, "w", encoding="utf8") as outf:
        outf.write(json.dumps(verdict, ensure_ascii=False, indent=4))

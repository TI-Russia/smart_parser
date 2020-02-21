import argparse
import json
import re
import os

def parse_args():
    smart_parser_default =  os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    "../../src/bin/Release/netcoreapp3.1/smart_parser"
            )
    if os.path.sep == "\\":
        smart_parser_default += ".exe"

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", dest='source_file', required=True)
    parser.add_argument("--txt-file", dest='txt_file', required=True)
    parser.add_argument("--output", dest='output', default=None)
    parser.add_argument("--smart-parser-binary",
                        dest='smart_parser_binary',
                        default=os.path.normpath(smart_parser_default))
    args = parser.parse_args()
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
    regexp = "[А-Я]\w+\s+[А-Я]\w+\s+[А-Я]\w+((вич)|(ьич)|(кич)|(вна)|(чна))" # # Сокирко Алексей Викторович
    if get_matches(re.finditer(regexp, input_text), result, name):
        pass
    else:
        regexp = "[А-Я]\w+\s+[А-Я]\.\s*[А-Я]\."   # Сокирко А.В.
        get_matches(re.finditer(regexp, input_text), result, name)


def find_relatives(input_text, result, name):
    regexp = "супруга|(несовершеннолетний ребенок)|сын|дочь|(супруг\b)"
    get_matches(re.finditer(regexp, input_text), result, name)


def find_vehicles(input_text, result, name):
    regexp = r"\b(Opel|Ситроен|Мазда|Mazda|Пежо|Peageut|BMV|БМВ|Ford|Форд|Toyota|Тойота|KIA|ТАГАЗ|Шевроле|Chevrolet|Suzuki|Сузуки|Mercedes|Мерседес|Renault|Рено|Мицубиси|Rover|Ровер|Нисан|Nissan|Ауди|Audi)\b"
    get_matches(re.finditer(regexp, input_text, re.IGNORECASE), result, name)


def find_vehicles_word(input_text, result, name):
    regexp = "транспорт"
    get_matches(re.finditer(regexp, input_text, re.IGNORECASE), result, name)


def find_income(input_text, result, name):
    regexp = '[0-9]{6}'
    get_matches(re.finditer(regexp, input_text.replace(' ', ''), re.IGNORECASE), result, name)


def find_realty(input_text, result, name):
    regexp = "квартира|(земельный участок)|(жилое\s+помещение)|комната|долевая"
    get_matches(re.finditer(regexp, input_text, re.IGNORECASE), result, name)


def find_header(input_text, result, name):
    regexps = [
        r"Сведения\*?\s+о\s+доходах",
        r"Сведения\*?\s+о\s+расходах",
        r"Сведения\s+об\s+имущественном\s+положении\s+и\s+доходах",
        r"Сведения\s+о\s+доходах,\s+об\s+имуществе\s+и\s+обязательствах",
        r"Сведения\s+о\s+доходах\s+федеральных\s+государственных",
        r"(Фамилия|ФИО).{1,200}Должность.{1,200}Перечень\s+объектов.{1,200}транспортных",
        r"Сведения\s+о\s+доходах.{1,200}Недвижимое\s+имущество.{1,200}Транспортное",
        r"Сведения\s*,?\s+предоставленные\s+руководителями",
        r"Сведения\s+об\s+источниках\s+получения\s+средств"
    ]
    input_text = input_text.strip()
    for regexp in regexps:
        if get_matches(re.finditer(regexp, input_text, re.IGNORECASE), result, name):
            break


def find_decree(input_text, result, name):
    regexp = "^(постановление|решение|доклад|протокол|план|указ)"
    get_matches(re.finditer(regexp, input_text.replace(' ', ''), re.IGNORECASE), result, name)


def process_smart_parser_json(json_file):
    with open(json_file, "r", encoding="utf8") as inpf:
        smart_parser_json = json.load(inpf)
        people_count = len(smart_parser_json.get("persons", []))
    os.remove(json_file)
    return people_count


def get_smart_parser_result(smart_parser_binary, source_file):
    if not os.path.exists(smart_parser_binary):
        raise Exception("cannot find {}".format(smart_parser_binary))

    if source_file.endswith("pdf"):  # cannot process new pdf without conversion
        return 0

    cmd = "{} -skip-relative-orphan -skip-logging  -adapter prod -fio-only {}".format(smart_parser_binary,
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


if __name__ == "__main__":
    args = parse_args()
    with open(args.txt_file, "r", encoding="utf8", errors="ignore") as inpf:
        input_text = inpf.read().replace("\n", " ").replace("\r", " ").replace ('"', ' ')
    result = {
        "result": "unknown",
        "smart_parser_person_count":  get_smart_parser_result(args.smart_parser_binary, args.source_file)
    }
    result["start_text"] = input_text[0:100]
    _, file_extension = os.path.splitext(args.source_file)
    if len (input_text) < 200:
        if file_extension in {".html", ".htm", ".docx", ".doc"}:
            result["result"] = "some_other_document"  # fast empty files
        else:
            result["description"] = "file is too short"
    elif result['smart_parser_person_count'] > 0:
        result["result"] = "declaration"
    else:
        find_person(input_text, result, "person")
        find_relatives(input_text, result, "relative") #not used
        find_vehicles(input_text, result, "auto")
        find_vehicles_word(input_text, result, "transport_word")
        find_income(input_text, result, "income") #not used
        find_realty(input_text, result, "realty")
        find_header(input_text, result, "header")
        find_decree(input_text, result, "decree")

        person_count = len(result.get('person', dict()).get('matches', list()))
        relative_count = len(result.get('relative', dict()).get('matches', list()))
        realty_count = len(result.get('realty', dict()).get('matches', list()))
        vehicle_count = len(result.get('auto', dict()).get('matches', list()))
        is_declaration = False
        if result.get('decree') is not None:
            pass
        elif vehicle_count > 0:
            is_declaration = True
        elif result.get("header", dict()).get("start", 1) == 0:
            is_declaration = True
        elif realty_count > 5:
            is_declaration = True
        elif person_count > 0 and result.get("header") is not None:
            if person_count > 2 and result["header"]['start'] < result["person"]['start']:
                is_declaration = True
            else:
                if realty_count > 0:
                    is_declaration = True

        result["result"] = "declaration" if is_declaration else "some_other_document"

    with open (args.output, "w", encoding="utf8") as outf:
        outf.write( json.dumps(result, ensure_ascii=False, indent=4) )

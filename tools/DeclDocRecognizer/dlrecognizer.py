import argparse
import json
import re


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", dest='input', required=True)
    parser.add_argument("--output", dest='output', default=None)
    args = parser.parse_args()
    return args


def find_person(input_text, result):
    regexp = "[А-Я]\w+\s+[А-Я]\w+\s+[А-Я]\w+((вич)|(ьич)|(кич)|(вна)|(чна))" # # Сокирко Алексей Викторович
    matches = tuple(re.finditer(regexp, input_text))
    if len(matches) > 0:
        result["person_matches"] = [str(x) for x in matches]
    else:
        regexp = "[А-Я]\w+\s+[А-Я]\.\s*[А-Я]\."   # Сокирко А.В.
        matches = tuple(re.finditer(regexp, input_text))
        if len(matches) > 0:
            result["person_matches"] = [str(x) for x in matches]


def find_vehicles(input_text, result):
    regexp = r"\b(Opel|Ситроен|Мазда|Mazda|Пежо|Peageut|BMV|БМВ|Ford|Форд|Toyota|Тойота|KIA|Шевроле|Chevrolet|Suzuki|Сузуки|Mercedes|Мерседес|Renault|Рено|Мицубиси|Rover|Ровер|Нисан|Nissan)\b"
    matches = tuple(re.finditer(regexp, input_text, re.IGNORECASE))
    if len(matches) > 0:
        result["auto_matches"] = [str(x) for x in matches]


def find_vehicles_word(input_text, result):
    regexp = "транспорт"
    matches = tuple(re.finditer(regexp, input_text, re.IGNORECASE))
    if len(matches) > 0:
        result["transport_word_matches"] = [str(x) for x in matches]


def find_income(input_text, result):
    regexp = '[0-9]{6}'
    matches = tuple(re.finditer(regexp, input_text.replace(' ', ''), re.IGNORECASE))
    if len(matches) > 0:
        result["income_matches"] = [str(x) for x in matches]


def find_realty(input_text, result):
    regexp = "квартира|(земельный участок)|(жилое\s+помещение)|комната"
    matches = tuple(re.finditer(regexp, input_text, re.IGNORECASE))
    if len(matches) > 0:
        result["realty_matches"] = [str(x) for x in matches]


def find_header(input_text, result):
    header_regexps = [
        "Сведения\s+о\sдоходах,\s+расходах",
        "Сведения\s+об\s+имущественном\s+положении\s+и\s+доходах",
        "Сведения\s+о\s+доходах,\s+об\s+имуществе\s+и\s+обязательствах",
        "Сведения\s+о\s+доходах\s+федеральных\s+государственных",
        "(Фамилия|ФИО).*Должность.*Перечень\s+объектов.*транспортных",
        "Сведения\s+о\s+доходах.*Недвижимое\s+имущество.*Транспортное",
        "Сведения\s*,?\s+предоставленные\sруководителями"
    ]
    input_text = input_text.strip()
    for r in header_regexps:
        matches = tuple(re.finditer(r, input_text, re.IGNORECASE))
        if len(matches) > 0:
            result["header_matches"] = [str(x) for x in matches]
            result["header_start"] = matches[0].start()
            break


if __name__ == "__main__":
    args = parse_args()
    with open(args.input, "r", encoding="utf8", errors="ignore") as inpf:
        input_text = inpf.read().replace("\n", " ").replace("\r", " ").replace ('"', ' ')
    result = {
        "result": "unknown"
    }
    if len (input_text) < 200:
        result["description"] = "file is too short"
    else:
        find_person(input_text, result)
        find_vehicles(input_text, result)
        find_vehicles_word(input_text, result)
        find_income(input_text, result)
        find_realty(input_text, result)
        find_header(input_text, result)

        person_count = len(result.get('person_matches', list()))
        realty_count = len(result.get('realty_matches', list()))
        is_declaration = False
        if result.get('auto_matches') is not None:
            is_declaration = True
        elif result.get("header_start", 1) == 0:
            is_declaration = True
        elif realty_count > 5:
            is_declaration = True
        elif person_count > 0 and result.get("header_matches") is not None:
            if person_count > 2:
                is_declaration = True
            else:
                if result.get("transport_word_matches") is not None and result.get("income_matches") is not None:
                    is_declaration = True
                if realty_count > 0:
                    is_declaration = True

        result["result"] = "declaration" if is_declaration else "some_other_document"
        result["start_text"] = input_text[0:100]



    with open (args.output, "w", encoding="utf8") as outf:
        outf.write( json.dumps(result, ensure_ascii=False, indent=4) )
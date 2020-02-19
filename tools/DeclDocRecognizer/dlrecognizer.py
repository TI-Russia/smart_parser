import argparse
import json
import re


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", dest='input', required=True)
    parser.add_argument("--output", dest='output', default=None)
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    with open(args.input, "r", encoding="utf8") as inpf:
        input_text = inpf.read().replace("\n", " ").replace("\r", " ").replace ('"', ' ')
    result = {
        "result": "unknown"
    }
    if len (input_text) < 200:
        result["description"] = "file is too short"
    else:
        result["start_text"] = input_text[0:100]
        result["result"] = "some_other_document"
        regexps = [
            "Сведения\s+о\sдоходах,\s+расходах",
            "Сведения\s+об\s+имущественном\s+положении\s+и\s+доходах",
            "Сведения\s+о\s+доходах,\s+об\s+имуществе\s+и\s+обязательствах",
            "Сведения\s+о\s+доходах\s+федеральных\s+государственных",
            "(Фамилия|ФИО).*Должность.*Перечень\s+объектов.*транспортных"
        ]
        for  r in regexps:
            reg = re.search(r, input_text, re.IGNORECASE)
            if reg is not None:
                result["regexp"] = r
                result["result"] = "declaration"
                break
    with open (args.output, "w", encoding="utf8") as outf:
        outf.write( json.dumps(result, ensure_ascii=False, indent=4) )
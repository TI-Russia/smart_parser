import urllib.request
import sys
from urllib.parse import urlparse, quote_plus, urlencode, quote
import json
import time

def get_metrics(text):
    data = urlencode({"text": text}, quote_via=quote).encode('latin')
    response = urllib.request.urlopen("http://api.plainrussian.ru/api/1.0/ru/measure/", data)
    html = response.read().decode("utf-8")
    return json.loads(html)


if __name__ == "__main__":
    with open(sys.argv[1], "r", encoding="utf8") as inpf:
        offices = json.load(inpf)

    for office in offices:
        print(office['office_name'])
        for t in office.get("filtered_texts", []):
            metrics = get_metrics (t['text'])
            t['metrics'] = metrics


    with open(sys.argv[1], "w", encoding="utf8") as outf:
        json.dump (offices, outf, indent=4, ensure_ascii=False)


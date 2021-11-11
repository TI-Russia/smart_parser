from office_db.russian_regions import TRussianRegions
from common.logging_wrapper import setup_logging

import json
import argparse
import requests


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", dest='input_file')
    parser.add_argument("--result-count", dest='result_count', type=int, default=10)
    parser.add_argument("--api-key", dest='api_key')
    return parser.parse_args()


def ask_yandex_map_api(apikey, org_name, result_count=1):
    url = 'https://search-maps.yandex.ru/v1/'
    params = {'apikey': apikey, 'lang': 'ru_RU', 'type': 'biz', 'results': result_count, 'text': org_name}
    result = requests.get(url, params=params)
    return json.loads(result.text)


def main():
    args = parse_args()
    logger = setup_logging("fetch_yandex_maps")
    with open(args.input_file) as inp:
        for l in inp:
            office_id, name = l.strip().split("\t")
            yandex_org = ask_yandex_map_api(args.api_key, name, args.result_count)
            if list(yandex_org.get('features', [])) == 0:
                logger.error("cannot find office id={}, name={}".format(office_id, name))
                print("\t".join([office_id, name, json.dumps({}, ensure_ascii=False)]))
            else:
                office = yandex_org['features'][0]['properties']['CompanyMetaData']
                print("\t".join([office_id, name, json.dumps(office, ensure_ascii=False)]))


#curl -G  'https://search-maps.yandex.ru/v1/?apikey=API_KEY&lang=ru_RU&type=biz&results=1' --data-urlencode "text=Отделение Пенсионного фонда Российской Федерации г. Байконур"

if __name__ == "__main__":
    main()
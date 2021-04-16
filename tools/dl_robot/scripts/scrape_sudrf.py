from common.http_request import make_http_request_urllib

import argparse
from bs4 import BeautifulSoup
import os
import logging
import json
import time


def setup_logging(logfilename="scrape_sudrf.log"):
    logger = logging.getLogger("scrape_sudrf")
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", dest='output_json')
    return parser.parse_args()


REGIONS = [
('54', 'Новосибирская область'),
('55', 'Омская область'),
('56', 'Оренбургская область'),
('57', 'Орловская область'),
('53', 'Новгородская область'),
('92', 'Город Севастополь'),
('78', 'Город Санкт-Петербург'),
('77', 'Город Москва'),
('95', 'Территории за пределами РФ'),
('29', 'Архангельская область'),
('28', 'Амурская область'),
('22', 'Алтайский край'),
('30', 'Астраханская область'),
('31', 'Белгородская область'),
('32', 'Брянская область'),
('33', 'Владимирская область'),
('34', 'Волгоградская область'),
('35', 'Вологодская область'),
('36', 'Воронежская область'),
('79', 'Еврейская автономная область'),
('75', 'Забайкальский край'),
('37', 'Ивановская область'),
('38', 'Иркутская область'),
('07', 'Кабардино-Балкарская Республика'),
('39', 'Калининградская область'),
('40', 'Калужская область'),
('41', 'Камчатский край'),
('09', 'Карачаево-Черкесская Республика'),
('42', 'Кемеровская область'),
('43', 'Кировская область'),
('44', 'Костромская область'),
('23', 'Краснодарский край'),
('24', 'Красноярский край'),
('45', 'Курганская область'),
('46', 'Курская область'),
('47', 'Ленинградская область'),
('48', 'Липецкая область'),
('49', 'Магаданская область'),
('50', 'Московская область'),
('51', 'Мурманская область'),
('83', 'Ненецкий автономный округ '),
('52', 'Нижегородская область'),
('58', 'Пензенская область'),
('59', 'Пермский край'),
('25', 'Приморский край'),
('60', 'Псковская область'),
('01', 'Республика Адыгея'),
('02', 'Республика Алтай'),
('03', 'Республика Башкортостан'),
('04', 'Республика Бурятия'),
('05', 'Республика Дагестан'),
('06', 'Республика Ингушетия'),
('08', 'Республика Калмыкия'),
('10', 'Республика Карелия'),
('11', 'Республика Коми'),
('91', 'Республика Крым'),
('12', 'Республика Марий Эл'),
('13', 'Республика Мордовия'),
('14', 'Республика Саха (Якутия)'),
('15', 'Республика Северная Осетия-Алания'),
('16', 'Республика Татарстан'),
('17', 'Республика Тыва'),
('19', 'Республика Хакасия'),
('61', 'Ростовская область'),
('62', 'Рязанская область'),
('63', 'Самарская область'),
('64', 'Саратовская область'),
('65', 'Сахалинская область'),
('66', 'Свердловская область'),
('67', 'Смоленская область'),
('26', 'Ставропольский край'),
('68', 'Тамбовская область'),
('69', 'Тверская область'),
('70', 'Томская область'),
('71', 'Тульская область'),
('72', 'Тюменская область'),
('18', 'Удмуртская Республика'),
('73', 'Ульяновская область'),
('27', 'Хабаровский край'),
('86', 'Ханты-Мансийский автономный округ - Югра (Тюменская область)'),
('74', 'Челябинская область'),
('20', 'Чеченская Республика'),
('21', 'Чувашская Республика - Чувашия'),
('87', 'Чукотский автономный округ'),
('89', 'Ямало-Ненецкий автономный округ'),
('76', 'Ярославская область'),
]

REGIONAL_COURT_URL = "https://sudrf.ru/index.php?id=300&act=go_search&searchtype=fs&court_subj={}"


def main():
    logger = setup_logging()
    courts = list()
    args = parse_args()
    for id, region_name in REGIONS:
        print(id)
        url = REGIONAL_COURT_URL.format(id)
        cache_file_name = "sudrf/{}.file_data.html".format(id)
        if os.path.exists(cache_file_name):
            with open(cache_file_name, "rb") as inp:
                file_data = inp.read()
        else:
            time.sleep(15)
            _, _, file_data = make_http_request_urllib(url, "GET")
            with open(cache_file_name, "wb") as outp:
                outp.write(file_data)
        soup = BeautifulSoup(file_data, "html.parser")
        search_results = soup.find('ul', attrs={'class': 'search-results'})
        for li in search_results.findAll('li'):
            name_ref = li.find('a', attrs={'class':'court-result'})
            name_anchor  = name_ref.get_text()
            name = name_anchor[0:name_anchor.find('(')].strip()
            region = name_anchor[name_anchor.find('('):].strip(' ()')
            if len(region.strip()) < 3:
                region = region_name
            link = None
            mail = None
            for a in li.find_all('a', href=True):
                href = a['href'].strip('/')
                if href.startswith('mailto:'):
                    mail = href[7:]
                else:
                    if href.endswith('sudrf.ru') or href.endswith('vsrf.ru') or href.endswith('mos.ru') or \
                        href.endswith('mos-gorsud.ru') or href.endswith('oblsudnn.ru') or \
                        href.endswith('govid=47'):
                        link = href
            #assert mail is not None
            assert link is not None


            for br in li.find_all("br"):
                br.replace_with("\n")
            text = li.get_text()
            address = None
            for l in text.split("\n"):
                if l.strip().startswith("Адрес: "):
                    address = l[7:].strip()

            record = {
                'name': name,
                'region':  region,
                'mail': mail,
                'link': link,
                'address': address
            }
            courts.append(record)
    with open (args.output_json, "w") as outp:
        outp.write(json.dumps(courts, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
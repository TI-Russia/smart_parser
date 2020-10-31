import json
import logging
import ssl
import urllib.parse
import argparse
import urllib.request
from collections import defaultdict
import mwclient

def setup_logging(logfilename="build_geo.log"):
    logger = logging.getLogger("build_thes")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(logfilename, "a+", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger

def send_sparql_request(sparql):
    sparql = urllib.parse.quote(sparql)
    url = 'https://query.wikidata.org/sparql?format=json&query=' + sparql
    context = ssl._create_unverified_context()
    req = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
    )
    with urllib.request.urlopen(req, context=context, timeout=600.0) as request:
        str = request.read().decode('utf-8')
        with open ("debug.txt", "w") as outp:
            outp.write(str)
        return json.loads(str)


def delete_http_prefix(u):
    prefix = 'http://www.wikidata.org/entity/'
    if u.startswith(prefix):
        u = u[len(prefix):]
    return u


def parse_list(u):
    res = list()
    for x in u.split('|'):
        x = delete_http_prefix(x).strip()
        if len(x) > 0:
            res.append(x)
    return res

SPARQL_QUERY = """
        SELECT DISTINCT ?geo ?geoLabel 
           ?populations 
           ?partofs
           ?superclasses 
           ?websites

        WHERE {
          {
            SELECT ?geo
                   ?geoLabel
                   (GROUP_CONCAT(DISTINCT ?partof; separator="|") as ?partofs)
                   (GROUP_CONCAT(DISTINCT ?population; separator="|") as ?populations)
                   (GROUP_CONCAT(DISTINCT ?website; separator="|") as ?websites)
                   (GROUP_CONCAT(DISTINCT ?superclass; separator="|") as ?superclasses)
            WHERE {
              ?geo wdt:P17 wd:Q159 .  # country Russia
              #?geo wdt:P31 wd:Q7930989 . # is a city - just for testing purpose
              ?geo wdt:P31 ?superclass .

              {
                ?geo wdt:P1082 ?population.
              }
              UNION  {
                 ?geo wdt:P1566 ?geonames 
              } .

              OPTIONAL {
                ?geo wdt:P856 ?website .
              }
              OPTIONAL {
                ?geo p:P131 ?partof_statement.
                ?partof_statement ps:P131 ?partof.
                FILTER NOT EXISTS{ 
                    ?partof_statement pq:P582 ?partof_end_time 
                }.
              }
            }
            GROUP BY ?geo ?geoLabel
          }

          SERVICE wikibase:label {
              bd:serviceParam wikibase:language "ru" .
          }
        }

"""

RussianMainRegionWithObsolete = {
"Белгородская область","Брянская область","Владимирская область","Воронежская область","Ивановская область",
"Калужская область","Костромская область","Курская область", "Липецкая область","Московская область",
"Орловская область","Рязанская область", "Смоленская область","Тамбовская область","Тверская область",
"Тульская область", "Ярославская область","Москва","Карелия","Республика Коми","Архангельская область",
"Вологодская область","Калининградская область","Ленинградская область","Мурманская область","Новгородская область",
"Псковская область","Санкт-Петербург", "Адыгея","Дагестан", "Ингушетия", "Кабардино-Балкария",
"Калмыкия", "Карачаево-Черкесия","Республика Северная Осетия-Алания", "Чечня",
"Краснодарский край", "Ставропольский край","Астраханская область", "Волгоградская область", "Ростовская область",
"Башкортостан", "Марий Эл", "Мордовия", "Татарстан", "Удмуртия",
"Чувашия", "Кировская область", "Нижегородская область","Оренбургская область","Пензенская область",
"Пермская область", "Коми-Пермяцкий автономный округ", "Самарская область","Саратовская область","Ульяновская область",
"Курганская область","Свердловская область","Тюменская область","Ханты-Мансийский автономный округ — Югра",
"Ямало-Ненецкий автономный округ", "Челябинская область","Республика Алтай", "Бурятия",
"Тыва", "Хакасия", "Алтайский край", "Красноярский край",
"Таймырский (Долгано-Ненецкий) автономный округ", "Иркутская область",
"Усть-Ордынский Бурятский автономный округ", "Кемеровская область", "Новосибирская область", "Омская область",
"Томская область","Читинская область","Агинский Бурятский автономный округ", "Якутия",
"Приморский край", "Хабаровский край", "Амурская область","Камчатский край",
"Магаданская область","Сахалинская область", "Еврейская автономная область", "Чукотский автономный округ",
"Республика Крым", "Симферополь"}


class TGeoThesBuilder:
    def __init__(self, filename):
        self.logger = setup_logging()
        self.file_name = "rus_geo.txt"
        self.thesaurus = dict()
        self.class_to_ru_label = dict()

    def initial_fetch_from_wikibase(self):
        self.thesaurus = {'entities': {}}
        all_russian_geo = send_sparql_request(SPARQL_QUERY)
        self.logger.info("start reading json from wikibase")
        for r in all_russian_geo['results']['bindings']:
            id = delete_http_prefix(r['geo']['value'])
            record = {
                'label': r['geoLabel']['value'],
                'superclasses': parse_list(r['superclasses']['value']),
                'partofs': parse_list(r['partofs']['value'])
            }
            populations = parse_list(r['populations']['value'])
            if len(populations) > 0:
                if populations[0].isdigit():
                    record['population'] = int(populations[0])
                else:
                    self.logger.error("cannot parse population=\"{}\" for id={}".format(populations[0], id))
            websites = parse_list(r['websites']['value'])
            if len(websites) > 0:
                record['websites'] = websites

            self.thesaurus['entities'][id] = record

    def write_to_disk(self):
        #self.thesaurus = {'entities': self.thesaurus}
        with open(self.file_name, "w") as outp:
            json.dump(self.thesaurus, outp, indent=4, ensure_ascii=False)

    def read_from_disk(self):
        with open(self.file_name, "r") as inp:
            self.thesaurus = json.load(inp)

    def get_class_with_populations(self):
        classes_with_populations = defaultdict(int)
        sum_population = defaultdict(int)
        for k,v in self.thesaurus['entities'].items():
            if v.get('population') is not None:
                for c in v['superclasses']:
                    classes_with_populations[c] += 1
                    sum_population[c] += v.get('population')

        for k, v in builder.thesaurus['geo_classes'].items():
            if k in classes_with_populations:
                v['have_popuplation_count'] = classes_with_populations[k]
                v['avg_popuplation'] = int(sum_population[c] / classes_with_populations[k])

    def get_class_names(self):
        classes = set()
        #print (self.thesaurus.keys())
        for v in self.thesaurus['entities'].values():
            classes.update(v['superclasses'])
        site = mwclient.Site('wikidata.org')
        self.thesaurus['geo_classes'] = dict()
        for c in classes:
            page = site.pages[c.strip()]
            wikibase_json = json.loads(page.text())

            self.thesaurus['geo_classes'][c]= {"label": wikibase_json['labels'].get('ru', {}).get('value', "unknown")}

    def calc_class_can_have_administration(self):
        minus_words = ['монтёрский', 'бывший', 'улица', 'урочище', 'будка', 'разъезд', 'Украины', 'волость',
                       'местоположение', 'Украине', 'демоним', 'Финляндии', 'казарма', 'островов', 'археологическое',
                       'национальность', 'кордон', 'вулкан', 'население', 'бывшая', 'империи', 'СССР', 'Франции',
                       'покинутый', 'этническое', 'наследия']
        for k, v in self.thesaurus['geo_classes'].items():
            if 'can_have_administration' in v:
                del v['can_have_administration']
            if v.get('have_popuplation_count', 0) > 1:
                if v.get('have_popuplation_count', 0) < 100:
                    label = v['label']
                    found_minus_word = False
                    for w in minus_words:
                        if label.find(w) != -1:
                            found_minus_word = True
                    if found_minus_word:
                        continue
                v['can_have_administration'] = True

    def calc_use_for_declarator(self):
        for k, v in self.thesaurus['entities'].items():
            population = v.get('population', 0)
            class_can_have_administration = False
            for c in v['superclasses']:
                class_info = self.thesaurus['geo_classes'].get(c, {})
                if class_info.get('avg_popuplation', 0) > 10000 and class_info.get('have_popuplation_count', 0) > 20:
                    if class_info.get('can_have_administration', False):
                        class_can_have_administration = True
            if class_can_have_administration or population > 1000:
                v['use_for_declarator'] = True

    def check_main_regions(self):
        rus_names = defaultdict(list)
        for k,v in self.thesaurus['entities'].items():
            rus_names[v['label']].append(k)

        for r in RussianMainRegionWithObsolete:
            if r not in rus_names:
                raise Exception("cannot find {} in thesaurus".format(r))


if __name__ == '__main__':
    builder = TGeoThesBuilder("rus_geo.txt")
    #builder.initial_fetch_from_wikibase()
    builder.read_from_disk()
    #builder.get_class_names()
    #builder.get_class_with_populations()
    #builder.calc_class_can_have_administration()
    #builder.calc_use_for_declarator()
    builder.check_main_regions()
    #builder.write_to_disk()

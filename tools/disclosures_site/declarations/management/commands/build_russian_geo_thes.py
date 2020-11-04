import json
import logging
import ssl
import urllib.parse
import urllib.request
from collections import defaultdict
import mwclient
import declarations.models as models
from django.core.management import BaseCommand
from declarations.models import SynonymClass
from .declination import set_colloc_to_genitive_case


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

class TGeoThesBuilder:
    def __init__(self, filename):
        self.logger = setup_logging()
        self.file_name = filename
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

    def get_population(self, wikibase_id):
        return self.thesaurus['entities'][wikibase_id].get ('population', 0)

    def copy_synonyms_from_sql_regions(self):
        rus_names = dict()
        for k,v in self.thesaurus['entities'].items():
            l = v['label'].lower()
            if l not in rus_names:
                rus_names[l] = k
            elif self.get_population(rus_names[l]) < self.get_population(k):
                rus_names[l] = k

        for r in models.Region.objects.all():
            wikidata_id = None
            if r.name == "Карачаево-Черкесская республика":
                wikidata_id = 'Q5328'
            elif r.name == "Республика Северная Осетия — Алания":
                wikidata_id = 'Q5237'
            elif r.name == "Республика Тува (Тыва)":
                wikidata_id = 'Q960'
            elif r.name == "Республика Саха (Якутия)":
                wikidata_id = 'Q6605'
            elif r.name.find('Крым') != -1:
                wikidata_id = 'Q15966495'
            elif r.name.find('Республика Алтай') != -1:
                wikidata_id = 'Q5971'
            else:
                for s in r.region_synonyms_set.all():
                    if s.synonym in rus_names:
                        wikidata_id = rus_names[s.synonym]
            if wikidata_id is None:
                raise Exception("cannot find {} in thesaurus".format(r.name))
            r.wikibase_id = wikidata_id
            synonyms = dict()
            for s in r.region_synonyms_set.all():
                synonyms[s.synonym] = s.synonym_class
            #sys.stderr.write("{} {} {}\n".format(wikidata_id, r.name, synonyms, self.get_population(wikidata_id)))
            assert self.get_population(wikidata_id) > 40000
            self.thesaurus['entities'][wikidata_id]['synonyms'] = synonyms
            self.thesaurus['entities'][wikidata_id]['federal_subject'] = True

    def add_synonym_from_name_if_missing(self):
        for k, v in self.thesaurus['entities'].items():
            if v.get('use_for_declarator', False):
                if 'synonyms' not in v:
                    v['synonyms'] = dict()
                    v['synonyms'][v['label'].lower()] = SynonymClass.Russian

    def add_gorod_as_a_type(self):
        for k,v in self.thesaurus['entities'].items():
            if "Q7930989" in v['superclasses']:
                new_syns = set()
                for s, sym_class in v.get('synonyms', {}).items():
                    if sym_class == SynonymClass.Russian:
                        new_syns.add("город " + s)
                        new_syns.add("г. " + s)
                for n in new_syns:
                    v['synonyms'][n] = SynonymClass.RussianWithType1Before

    def generate_genitive(self):
        for k,v in self.thesaurus['entities'].items():
            if v.get('use_for_declarator', False):
                for s, syn_class in v['synonyms'].items():
                    if not SynonymClass.is_russian_nominative(syn_class):
                        continue
                    for f in set_colloc_to_genitive_case(self.logger, s, syn_class):
                        if f not in v['synonyms']:
                            v['synonyms'][f] = SynonymClass.RussianGenitive



class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            '--rus-thes-file',
            dest='rus_thes_file',
            required=True,
        )

    def handle(self, *args, **options):
        builder = TGeoThesBuilder(options['rus_thes_file'])
        # builder.initial_fetch_from_wikibase()
        builder.read_from_disk()
        # builder.get_class_names()
        # builder.get_class_with_populations()
        # builder.calc_class_can_have_administration()
        # builder.calc_use_for_declarator()
        # builder.copy_synonyms_from_sql_regions()
        # builder.add_synonym_from_name_if_missing()
        # builder.add_gorod_as_a_type()
        #assert len(json.loads(aot.synthesize("бай-тал", "N"))['forms']) == 0
        #builder.generate_genitive()
        #builder.write_to_disk()

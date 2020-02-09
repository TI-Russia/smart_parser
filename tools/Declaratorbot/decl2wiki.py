import json
import logging
import ssl
import pymysql
import pywikibot
import urllib.parse
import argparse
import urllib.parse
import re
import time

# Create a custom logger
def setup_logging( logger, logfilename):
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)




def send_json_request_to_ruwiki(title, api_action):
    title = title.replace(' ', '_')
    title = urllib.parse.quote(title)
    url = 'http://ru.wikipedia.org/w/api.php?action=query&format=json&formatversion=2'
    url += '&titles='+title
    if not api_action.startswith('&'):
        url += '&'
    url += api_action

    context = ssl._create_unverified_context()
    req = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
    )
    with urllib.request.urlopen(req, context=context, timeout=20.0) as request:
        return json.loads(request.read().decode('utf-8'))

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
    with urllib.request.urlopen(req, context=context, timeout=20.0) as request:
        return json.loads(request.read().decode('utf-8'))


#def get_wikidata_id_from_ruwiki(title):
#    response = send_json_request_to_ruwiki(title, 'prop=pageprops&ppprop=wikibase_item')
#    pages = response.get ("query", dict()).get("pages", list())
#    if len (pages) > 0:
#        return pages[0].get("pageprops", dict()).get("wikibase_item")
#    return None


def get_title_from_wiki_link(url, normalize=False):
    prefix = 'https://ru.wikipedia.org/wiki/'
    if url.startswith(prefix):
        fio = url[len(prefix):]
        fio = urllib.parse.unquote(fio)
        fio = fio.replace('_', ' ')
        if normalize:
            response = send_json_request_to_ruwiki(fio, 'redirects')
            redirects = response.get('query', dict()).get('redirects', list())
            if len(redirects) > 0:
                 return redirects[0]['to']
            normalized = response.get('query', dict()).get('normalized', list())
            if len(normalized) > 0:
                return normalized[0]['to']
        return fio
    else:
        logger = logging.getLogger("dlwikibot")
        logger.error("unknown link type {}".format(url))
        return url


def get_wikidata_item(title):
    site = pywikibot.Site('ru', 'wikipedia')
    page = pywikibot.Page(site, title)
    assert page.exists()
    item = pywikibot.ItemPage.fromPage(page)
    return item


def read_json(filename):
    with open(filename, "r", encoding="utf8") as inp:
        return json.load(inp)

def write_json(filename, records):
    with open(filename, "w", encoding="utf8") as outf:
        json.dump(records, outf, ensure_ascii=False, indent=4)


def get_all_wiki_links_from_db():
    db = pymysql.connect(db="declarator",user="declarator",password="declarator", unix_socket="/var/run/mysqld/mysqld.sock" )
    cursor = db.cursor()
    query = ("select id, wikipedia from declarations_person where wikipedia is not null and wikipedia <> '';")
    cursor.execute(query)
    result = dict()
    for (id, wikipedia_link) in cursor:
        normalize = True if wikipedia_link.find(',') == -1 else False
        fio = get_title_from_wiki_link(wikipedia_link, normalize=normalize)
        result[str(id)] = fio
    cursor.close()
    db.close()
    return result


def compare_sets (db_links, wikidata_pages):
    ruwikis = set()
    logger = logging.getLogger("dlwikibot")
    for wikidata_page in wikidata_pages:
        ruwikis.add(wikidata_page['ruwiki_title'])
        person_id = wikidata_page['person_id'],
        comp_res = {
                'decl_person_id': person_id,
                'wikidata': {
                    'url': wikidata_page['wikidata_url'],
                    'ruwiki_title': wikidata_page['ruwiki_title']
                },
                'decl_db_reference': {}
        }
        if person_id in db_links:
            comp_res['decl_db_reference']['ruwiki_title'] = db_links[person_id]
        yield comp_res

    site = pywikibot.Site('ru', 'wikipedia')
    for person_id, ruwiki_title in db_links.items():
        if ruwiki_title not in ruwikis:
            try:
                page = pywikibot.Page(site, ruwiki_title)
            except pywikibot.exceptions.Error as err:
                logger.error("cannot find in ruwiki title \"{}\", err = {}".format(ruwiki_title, err))
                continue
            comp_res = {
                'decl_person_id': person_id,
                'wikidata': {},
                'decl_db_reference': {
                    "ruwiki_title": ruwiki_title
                }
            }
            yield comp_res


def print_all (diff):
    for res_comp in diff:
        print(json.dumps(res_comp, ensure_ascii=False))


def get_wikidata_data_repository(wikidata_id):
    page = pywikibot.ItemPage(wikidata_id)
    return page.data_repository()


def add_missing_to_wikidata (diff):
    repo = pywikibot.Site().data_repository()
    wikidata_bot = pywikibot.WikidataBot(always=True)
    wikidata_bot.options['always'] = True
    cnt = 0
    logger = logging.getLogger("dlwikibot")
    for res_comp in diff:
        ruwiki_title = res_comp['wikidata'].get('ruwiki_title')
        if ruwiki_title is not None: # there is a link from wikidata to ruwiki
            continue
        ruwiki_title = res_comp['decl_db_reference']['ruwiki_title']
        person_id = res_comp['decl_person_id']
        item = get_wikidata_item(ruwiki_title)

        item.get() #  mysterious spell,  see https://www.mediawiki.org/wiki/Manual:Pywikibot/Wikidata/ru
        if item.claims.get("P1883") != None:
            logger.info ("skip {}, since it has already a link to declarator".format(ruwiki_title))
            continue
        claim = pywikibot.Claim(repo, "P1883")
        claim.setTarget(person_id)
        logger.info("set link from {} to declarator person id = {}".format(ruwiki_title, person_id))
        wikidata_bot.user_add_claim_unless_exists(item, claim.copy(), summary="add declarator.org id (P1883)")
        cnt += 1
        #if cnt >= 0:
        #    break

def get_template_regexp(wiki_template):
    vars = set()
    vars.add(wiki_template)
    response = send_json_request_to_ruwiki('Шаблон:'+ wiki_template, 'prop=redirects')
    pages = response.get('query', dict()).get('pages', list())
    assert len(pages) > 0
    for redirect in pages[0].get('redirects', list()):
        title = redirect['title']
        if title.find(':') != -1:
            title = title[title.find(':') + 1:]
        vars.add(title)

    # first char is case insensitive
    for v in list(vars):
        if v[0].isupper():
            vars.add (v[0].lower() + v[1:])
        else:
            vars.add(v[0].upper() + v[1:])

    regexp = r"\{\{\s*(" + "|".join(vars) + r")\s*\}\}"
    return re.compile(regexp)


def add_missing_template_to_ruwiki (diff, sleep_after_insert, max_insert_count):
    site = pywikibot.Site('ru', 'wikipedia')
    wiki_template = 'Внешние ссылки'
    wiki_template_regexp = get_template_regexp(wiki_template)
    logger = logging.getLogger("dlwikibot")
    insert_count = 0
    for res_comp in diff:
        ruwiki_title = res_comp['wikidata'].get('ruwiki_title')
        if ruwiki_title is None: # there is no link from wikidata to ruwiki
            continue
        page = pywikibot.Page(site, ruwiki_title)
        assert page.exists()
        text = page.get()
        logger.info("check {}".format(ruwiki_title))
        search_template =  re.search(wiki_template_regexp, text)
        if search_template is None:
            index_categ = text.find('[[Категория:')
            if index_categ == -1:
                logger.info("cannot find a category in {}, skip it".format(ruwiki_title))
                continue

            text = text[:index_categ] + '{{' + wiki_template + '}}\n\n' + text[index_categ:]
            page.text = text
            page.save(summary="добавляю темплейт {{"+wiki_template+'}}' )
            logger.info('inserted template {} to {}'.format(wiki_template, ruwiki_title))
            insert_count += 1
            if insert_count >= max_insert_count:
                break
            logger.info('sleep  {} seconds'.format(sleep_after_insert))
            time.sleep(sleep_after_insert)


def request_wikidata_pages_with_declarator_links():
    query = """
    SELECT ?wikidata_id ?sitelink ?person_id
    WHERE 
    {
      ?wikidata_id wdt:P1883 ?person_id.
      OPTIONAL {
        ?sitelink schema:about ?wikidata_id;
                schema:inLanguage "ru" ;
                schema:isPartOf [ wikibase:wikiGroup "wikipedia" ] .
        }
    }
    """
    data = send_sparql_request(query)
    records = list()
    for item in data['results']['bindings']:
        ruwiki_link = item.get('sitelink', {}).get("value")
        if ruwiki_link is None:
            continue
        fio = get_title_from_wiki_link(ruwiki_link)
        record = {
            'wikidata_url': item['wikidata_id']["value"],
            'person_id': item['person_id']["value"],
            'ruwiki_title': fio
        }
        records.append(record)
    return records

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="print")
    parser.add_argument("--wikidata-squeeze", dest='wikidata_squeeze_file')
    parser.add_argument("--db-squeeze", dest='db_squeeze_file')
    parser.add_argument("--sleep-after-insert", dest="sleep_after_insert", type=int, default=60)
    parser.add_argument("--max-insert-count", dest="max_insert_count", type=int, default=20)
    return parser.parse_args()


if __name__ == '__main__':
    #title = get_title_from_wiki_link('https://ru.wikipedia.org/wiki/%D0%9F%D1%83%D1%82%D0%B8%D0%BD,_%D0%92%D0%BB%D0%B0%D0%B4%D0%B8%D0%BC%D0%B8%D1%80_%D0%92%D0%BB%D0%B0%D0%B4%D0%B8%D0%BC%D0%B8%D1%80%D0%BE%D0%B2%D0%B8%D1%87')
    #title = get_title_from_wiki_link('https://ru.wikipedia.org/wiki/%D0%92%D0%BB%D0%B0%D0%B4%D0%B8%D0%BC%D0%B8%D1%80_%D0%92%D0%BB%D0%B0%D0%B4%D0%B8%D0%BC%D0%B8%D1%80%D0%BE%D0%B2%D0%B8%D1%87_%D0%9F%D1%83%D1%82%D0%B8%D0%BD', True)

    #get_wikidata_item('Абельцев, Сергей Николаевич')
    #get_wikidata_item('Крупенников, Владимир Александрович')
    #request_wikidata_pages_with_declarator_links()

    args = parse_args()
    logger = logging.getLogger("dlwikibot")
    setup_logging(logger, "dlwikibot.log")

    if args.action == "build_wikidata_squeeze_file":
        write_json( args.wikidata_squeeze_file, request_wikidata_pages_with_declarator_links())
    elif args.action == "build_db_squeeze_file":
        write_json( args.db_squeeze_file, get_all_wiki_links_from_db())
    else:
        db_links = read_json(args.db_squeeze_file)
        wikidata_links = read_json(args.wikidata_squeeze_file)
        diff = compare_sets(db_links, wikidata_links)
        if args.action == "print":
            print_all(diff)
        elif args.action == "add_missing_to_wikidata":
            add_missing_to_wikidata(diff)
        elif args.action == "add_template_to_ruwiki":
            add_missing_template_to_ruwiki(diff, args.sleep_after_insert, args.max_insert_count)
        else:
            print ("unknown action")

      


import json
import logging
import ssl
import pymysql
import pywikibot
import urllib.parse
import argparse
import urllib.parse
import re
import os

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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="print")
    parser.add_argument("--wikidata-links", dest='wikidata_links_file')
    return parser.parse_args()


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


def read_wiki_data_links(filename):
    with open(filename, "r", encoding="utf8") as inp:
        for l in inp:
            (wikidata, ruwiki, decl_person_id) = l.strip().split("\t")
            if ruwiki == "sitelink":
                continue
            fio = get_title_from_wiki_link(ruwiki)
            yield (wikidata, fio, decl_person_id)


def get_all_wiki_links_from_db():
    db = pymysql.connect(db="declarator",user="declarator",password="declarator", unix_socket="/var/run/mysqld/mysqld.sock" )
    cursor = db.cursor()
    query = ("select id, wikipedia from declarations_person where wikipedia is not null and wikipedia <> '';")
    cursor.execute(query)
    for (id, wikipedia_link) in cursor:
        normalize = True if wikipedia_link.find(',') == -1 else False
        fio = get_title_from_wiki_link(wikipedia_link, normalize=normalize)
        yield (str(id), fio)
    cursor.close()
    db.close()


def compare_sets (db_links, wikidata_links):
    ruwikis = set()
    logger = logging.getLogger("dlwikibot")
    for wikidata, ruwiki, decl_person_id in wikidata_links:
        ruwikis.add(ruwiki)
        comp_res = {
            'wikidata': wikidata,
            'ruwiki_title_from_wikidata': ruwiki,
            'decl_person_id':  decl_person_id
        }
        if decl_person_id in db_links:
            new_link = False
            if ruwiki != db_links[decl_person_id]:
                comp_res['diff_link'] = True
                comp_res['ruwiki_title_from_db'] = db_links[decl_person_id]
        else:
            comp_res["new_link"] = True
        yield comp_res

    site = pywikibot.Site('ru', 'wikipedia')
    for person_id, ruwiki_title in db_links.items():
        if ruwiki_title not in ruwikis:
            try:
                page = pywikibot.Page(site, ruwiki_title)
                yield {"missing": True, "person_id": person_id, "ruwiki_title_from_db": ruwiki_title}
            except pywikibot.exceptions.Error as err:
                logger.error("cannot find in ruwiki title \"{}\", err = {}".format(ruwiki_title, err))


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
        if res_comp.get('missing', False):
            ruwiki_title = res_comp['ruwiki_title_from_db']
            item = get_wikidata_item(ruwiki_title)
            item.get() #  mysterious spell,  see https://www.mediawiki.org/wiki/Manual:Pywikibot/Wikidata/ru
            if item.claims.get("P1883") != None:
                logger.info ("skip {}, since it has already a link to declarator".format(ruwiki_title))
                continue
            claim = pywikibot.Claim(repo, "P1883")
            claim.setTarget(res_comp['person_id'])
            logger.info("set link from {} to declarator person id = {}".format(ruwiki_title, res_comp['person_id']))
            wikidata_bot.user_add_claim_unless_exists(item, claim.copy(), summary="add declarator.org id (P1883)")
            cnt += 1
            if cnt >= 3:
                break

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

    regexp = '{{\s*' + "|".join(vars) + '\s*}}'
    return re.compile(regexp)


def add_missing_template_to_ruwiki (diff):
    site = pywikibot.Site('ru', 'wikipedia')
    wiki_template = 'Внешние ссылки'
    wiki_template_regexp = get_template_regexp(wiki_template)
    logger = logging.getLogger("dlwikibot")
    start = False
    for res_comp in diff:
        if 'missing' not in res_comp:
            ruwiki_title = res_comp['ruwiki_title_from_wikidata']
            if ruwiki_title == "Саввиди, Иван Игнатьевич":
                start = True
            if not  start:
                continue
            page = pywikibot.Page(site, ruwiki_title)
            assert page.exists()
            text = page.get()
            logger.info("check {}".format(ruwiki_title))
            if re.search(wiki_template_regexp, text) is None:
                index_categ = text.find('[[Категория:')
                if index_categ == -1:
                    logger.info("cannot find a category in {}, skip it".format(ruwiki_title))
                    continue

                text = text[:index_categ] + '{{' + wiki_template + '}}\n' + text[index_categ:]
                page.text = text
                page.save(summary="добавляю темплейт {{"+wiki_template+'}}' )
                logger.info('inserted template {} to {}'.format(wiki_template, ruwiki_title))
                #break

if __name__ == '__main__':
    #title = get_title_from_wiki_link('https://ru.wikipedia.org/wiki/%D0%9F%D1%83%D1%82%D0%B8%D0%BD,_%D0%92%D0%BB%D0%B0%D0%B4%D0%B8%D0%BC%D0%B8%D1%80_%D0%92%D0%BB%D0%B0%D0%B4%D0%B8%D0%BC%D0%B8%D1%80%D0%BE%D0%B2%D0%B8%D1%87')
    #title = get_title_from_wiki_link('https://ru.wikipedia.org/wiki/%D0%92%D0%BB%D0%B0%D0%B4%D0%B8%D0%BC%D0%B8%D1%80_%D0%92%D0%BB%D0%B0%D0%B4%D0%B8%D0%BC%D0%B8%D1%80%D0%BE%D0%B2%D0%B8%D1%87_%D0%9F%D1%83%D1%82%D0%B8%D0%BD', True)

    #get_wikidata_item('Абельцев, Сергей Николаевич')
    #get_wikidata_item('Крупенников, Владимир Александрович')

    args = parse_args()
    logger = logging.getLogger("dlwikibot")
    setup_logging(logger, "dlwikibot.log")

    db_links = dict(get_all_wiki_links_from_db())
    wikidata_links = read_wiki_data_links(args.wikidata_links_file)
    diff = compare_sets(db_links, wikidata_links)
    if args.action == "print":
        print_all(diff)
    elif args.action == "add_missing_to_wikidata":
        add_missing_to_wikidata(diff)
    elif args.action == "add_missing_to_ruwiki":
        add_missing_template_to_ruwiki(diff)
    else:
        print ("unknown action")

      


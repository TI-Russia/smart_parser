from common.logging_wrapper import setup_logging
from common.wiki_bots import send_sparql_request
import sys
import os
sys.path.insert(0,'pywikibot')
os.environ['PYWIKIBOT_DIR'] = 'pywikibot'
import pywikibot


import json
import gzip

sparql = """
    SELECT ?item ?itemLabel ?website
    WHERE
    {
      ?item wdt:P856 ?website.
      ?item wdt:P625 ?location.
      ?item wdt:P17 wd:Q159.
      SERVICE wikibase:label { bd:serviceParam wikibase:language "ru". }
    }
"""


def read_geo_with_sites(file_name):
    urls = dict()
    with open(file_name) as inp:
        wikidata = json.load(inp)
        for item in wikidata['results']['bindings']:
            url = item.get('website', {}).get("value")
            if url.startswith('http://'):
                url = url[7:]
            if url.startswith('https://'):
                url = url[8:]
            if url.startswith('www.'):
                url = url[4:]
            url = url.strip('/')
            wikidata_item = item.get('item', {}).get("value")
            urls[url] = wikidata_item
    return urls

#https://www.mediawiki.org/wiki/Manual:Pywikibot/Wikidata/ru
def delete_link(url, wikidata_item):
    repo = pywikibot.Site().data_repository()
    wikidata_bot = pywikibot.WikidataBot(always=True)
    wikidata_bot.options['always'] = True
    site = pywikibot.Site('wikidata', 'wikidata')
    item_page = pywikibot.ItemPage(site, wikidata_item)
    assert item_page.exists()
    item_page.get()
    if item_page.claims:
        if 'P856' in item_page.claims:
            print(item_page.claims['P856'][0].getTarget())
            print ("aaa")


def delete_links(logger, urls, markup_file):
    with gzip.open(markup_file) as inp:
        for line in inp:
            mark, url, reach_status, title = line.decode('utf8').strip().split("\t")
            if mark == "0":
                if url.startswith('www.'):
                    url = url[4:]
                url = url.strip('/')
                if url in urls:
                    logger.info("{}\t{}".format(url, urls[url]))


if __name__ == '__main__':
    logger = setup_logging(log_file_name="dlwikibot.log")

    wikidata_file = "geo_from_wikidata.json"
    #data = send_sparql_request(sparql)
    #with open (wikidata_file, "w") as outp:
    #    json.dump(data, outp)
    #urls = read_geo_with_sites(wikidata_file)
    #markup_file = "../disclosures_site/data/web_sites_markup.txt.gz"
    #delete_links(logger, urls, markup_file)
    #delete_link("http://www.verhnedon.ru/", "https://www.wikidata.org/wiki/Q2220876")
    delete_link("http://www.verhnedon.ru/", "Q2220876")
#https://www.wikidata.org/wiki/Q2220876


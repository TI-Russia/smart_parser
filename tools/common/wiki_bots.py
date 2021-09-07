import ssl
import urllib.parse
import urllib.request
import json


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

    with urllib.request.urlopen(req, context=context, timeout=60.0) as request:
        data = request.read().decode('utf-8')
        with open("sparql_raw_response.txt", "w") as outp:
            outp.write(data)
        return json.loads(data)


def get_title_from_wiki_link(logger, url, normalize=False):
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
        logger.error("unknown link type {}".format(url))
        return url


def get_wikidata_data_repository(wikidata_id):
    page = pywikibot.ItemPage(wikidata_id)
    return page.data_repository()


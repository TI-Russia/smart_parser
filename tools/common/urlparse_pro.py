import urllib.parse
import re


def urlsplit_pro(url):
    url = re.sub(r'^(https?)://(/+)', r'\1://', url)  # https:////petushki.info -> http://petushki.info ->
    if not url.startswith('http') and not url.startswith('//') and url[1:10].find('://') == -1:
        url = "//" + url
    return urllib.parse.urlsplit(url)

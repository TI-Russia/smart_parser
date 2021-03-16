import urllib.parse
import re
import socket
from .html_parser import THtmlParser
import hashlib
import os

def normalize_whitespace(str):
    str = re.sub(r'\s+', ' ', str)
    str = str.strip()
    return str


def strip_viewer_prefix(href):
    if href is None:
        return href
    # https://docs.google.com/viewer?url=https%3A%2F%2Foren-rshn.ru%2Findex.php%3Fdo%3Ddownload%26id%3D247%26area%3Dstatic%26viewonline%3D1
    viewers = ['https://docs.google.com/viewer?url=',
                'https://docviewer.yandex.ru/?url=',
                'https://view.officeapps.live.com/op/embed.aspx?src=',
                'https://view.officeapps.live.com/op/view.aspx?src=']
    for prefix in viewers:
        if href.startswith(prefix):
            href = href[len(prefix):]
            return urllib.parse.unquote(href)
    return href


def strip_html_url(url):
    if url.endswith('.html'):
        url = url[:-len('.html')]
    if url.endswith('.htm'):
        url = url[:-len('.htm')]
    if url.startswith('http://'):
        url = url[len('http://'):]
    if url.startswith('http://'):
        url = url[len('https://'):]
    if url.startswith('www.'):
        url = url[len('www.'):]
    return url


def normalize_and_russify_anchor_text(text):
    if text is not None:
        text = text.strip(' \n\t\r"').lower()
        text = " ".join(text.split()).replace("c", "с").replace("e", "е").replace("o", "о")
        return text
    return ""


def get_site_domain_wo_www(url):
    if url is None or len(url) == 0:
        return ""

    if not re.search(r'^[A-Za-z0-9+.\-]+://', url):
        url = 'http://{0}'.format(url)
    domain = urllib.parse.urlparse(url).netloc
    if domain.startswith('www.'):
        domain = domain[len('www.'):]
    return domain


def prepare_for_logging(s):
    if s is None:
        return ""
    s = s.translate(str.maketrans(
        {"\n": " ",
         "\t": " ",
         "\r": " "}))
    return s.strip()


def get_html_title(html):
    try:
        if soup.title is None:
            return ""
        return soup.title.string.strip(" \n\r\t")
    except Exception as err:
        return ""


def convert_timeout_to_seconds(s):
    if isinstance(s, int):
        return s
    seconds_per_unit = {"s": 1, "m": 60, "h": 3600}
    if s is None or len(s) == 0:
        return 0
    if seconds_per_unit.get(s[-1]) is not None:
        return int(s[:-1]) * seconds_per_unit[s[-1]]
    else:
        return int(s)


def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        print(ex)
        return False


def string_contains_Russian_name(name):
    if name.find('(') != -1:
        name = name[:name.find('(')].strip()
    words = name.split(' ')

    relatives = {"супруг", "супруга", "сын", "дочь"}
    while len(words) > 0 and words[-1].lower() in relatives:
        words = words[0:-1]

    if len(words) >= 0 and re.search('^[0-9]+[.]\s*$', words[0]) is not None:
        words = words[1:]

    if len(words) >= 3 and words[0].title() == words[0] and words[1].title() == words[1] and \
            words[2].strip(',-').lower()[-3:] in {"вич", "вна", "мич", "ьич", "тич", "чна"}:
        return True


    if len(words) >= 3 and words[-3].title() == words[-3] and words[-2].title() == words[-2] and \
            words[-1].strip(',-').lower()[-3:] in {"вич", "вна", "мич", "ьич", "тич", "чна"}:
        return True

    name = " ".join(words)
    if re.search('[А-Я]\s*[.]\s*[А-Я]\s*[.]\s*$', name) is not None:
        return True

    # Иванов И.И.
    if re.search('^[А-Я][а-я]+\s+[А-Я]\s*[.]\s*[А-Я]\s*[.]', name) is not None:
        return True

    # И.И. Иванов
    if re.search('[А-Я]\s*[.]\s*[А-Я]\s*[.][А-Я][а-я]+$', name) is not None:
        return True
    return False


def prepare_russian_names_for_search_index(str):
    if str is None:
        return None
    str = str.replace("Ё", "Е").replace("ё", "е")
    return str


def build_dislosures_sha256_by_file_data(file_data, file_extension):
    if file_extension == '.html':
        text = THtmlParser(file_data).get_text()
        file_data = text.encode("utf-8", errors="ignore")
    return hashlib.sha256(file_data).hexdigest()


def build_dislosures_sha256(file_path):
    _, file_extension = os.path.splitext(file_path)
    with open(file_path, "rb") as f:
        return build_dislosures_sha256_by_file_data(f.read(), file_extension)

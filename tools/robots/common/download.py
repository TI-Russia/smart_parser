import ssl
import urllib.parse
import urllib.request
import json
import re
from urllib.parse import urlparse, quote, unquote, urlunparse
import hashlib
from collections import defaultdict
import logging
from unidecode import unidecode
import os
import datetime
import time
import requests
from lxml.html import fromstring

FILE_CACHE_FOLDER = "cached"
DEFAULT_HTML_EXTENSION = ".html"
DEFAULT_ZIP_EXTENSION = ".zip"
ACCEPTED_DECLARATION_FILE_EXTENSIONS = {'.doc', '.pdf', '.docx', '.xls', '.xlsx', '.rtf', '.zip', DEFAULT_HTML_EXTENSION}

HEADER_MEMORY_CACHE = dict()
HEADER_REQUEST_COUNT = defaultdict(int)
ALL_HTTP_REQUEST = dict() # (url, method) -> time


def get_request_rate(min_time=0):
    global ALL_HTTP_REQUEST
    current_time = time.time()
    time_points = list(t for t in ALL_HTTP_REQUEST.values() if t > min_time)
    return {
        "request_rate_1_min": sum( 1 for t in time_points if (current_time - t) < 60),
        "request_rate_10_min": sum(1 for t in time_points if (current_time - t) < 60 * 10),
        "request_count": len(time_points)
    }


def wait_until_policy_compliance(policy_name, max_policy_value):
    request_rates = get_request_rate()
    sleep_sec = max_policy_value / 10
    while request_rates[policy_name] > max_policy_value:
        logger = logging.getLogger("dlrobot_logger")
        logger.debug("wait {} seconds to comply {} (max value={})".format(sleep_sec, policy_name, max_policy_value))
        time.sleep(sleep_sec)
        request_rates = get_request_rate()


def consider_request_policy(url, method):
    global ALL_HTTP_REQUEST
    if len(ALL_HTTP_REQUEST) > 80:
        wait_until_policy_compliance("request_rate_1_min", 50)
        wait_until_policy_compliance("request_rate_10_min", 300)

    ALL_HTTP_REQUEST[(url, method)] = time.time()


def is_html_contents(info):
    content_type = info.get('Content-Type', "text").lower()
    return content_type.startswith('text')


def make_http_request(url, method):

    consider_request_policy(url, method)

    o = list(urlparse(url)[:])
    if has_cyrillic(o[1]):
        o[1] = o[1].encode('idna').decode('latin')

    o[2] = unquote(o[2])
    o[2] = quote(o[2])
    url = urlunparse(o)
    context = ssl._create_unverified_context()
    req = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
    )
    logger = logging.getLogger("dlrobot_logger")
    logger.debug("urllib.request.urlopen ({}) method={}".format(url, method))
    with urllib.request.urlopen(req, context=context, timeout=20.0) as request:
        data = '' if method == "HEAD" else request.read()
        info = request.info()
        headers = request.headers
        return info, headers, data


def get_proxies():
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    parser = fromstring(response.text)
    proxies = set()
    for i in parser.xpath('//tbody/tr')[:10]:
        #if i.xpath('.//td[7][contains(text(),"yes")]'):
            proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
            proxies.add(proxy)
    return list(proxies)

LAST_HEAD_REQUEST_TIME = datetime.datetime.now()
PROXIES = get_proxies()

def request_url_headers (url):
    global HEADER_MEMORY_CACHE, HEADER_REQUEST_COUNT, LAST_HEAD_REQUEST_TIME, PROXIES
    if url in HEADER_MEMORY_CACHE:
        return HEADER_MEMORY_CACHE[url]
    if HEADER_REQUEST_COUNT[url] >= 3:
        raise Exception("too many times to get headers that caused exceptions")

    #os.environ['HTTP_PROXY'] = random.choice(PROXIES)
    #os.environ['HTTPS_PROXY'] = random.choice(PROXIES)
    #proxy = random.choice(PROXIES)

    # do not ddos sites
    elapsed_time = datetime.datetime.now() - LAST_HEAD_REQUEST_TIME
    if elapsed_time.total_seconds() < 1:
        time.sleep(1)
    LAST_HEAD_REQUEST_TIME = datetime.datetime.now()


    HEADER_REQUEST_COUNT[url] += 1
    _, headers, _ = make_http_request(url, "HEAD")
    #headers = requests.head(url, proxies={"http": proxy, "https": proxy})
    HEADER_MEMORY_CACHE[url] = headers
    return headers


def find_simple_js_redirect(data):
    res = re.search('((window|document).location\s*=\s*[\'"]?)([^"\']+)([\'"]?\s*;)', data)
    if res:
        url = res.group(3)
        return url
    return None


def has_cyrillic(text):
    return bool(re.search('[Ёёа-яА-Я]', text))


def get_site_domain_wo_www(url):
    url = "http://" + url.split("://")[-1]
    domain = urlparse(url).netloc
    if domain.startswith('www.'):
        domain = domain[len('www.'):]
    return domain




def download_with_urllib (url, search_for_js_redirect=True):
    info, headers, data = make_http_request(url, "GET")

    try:
        if is_html_contents(info):
            if search_for_js_redirect:
                try:
                    redirect_url = find_simple_js_redirect(data.decode('latin', errors="ignore"))
                    if redirect_url is not None and redirect_url != url:
                        return download_with_urllib(redirect_url, search_for_js_redirect=False)
                except Exception as err:
                    pass

    except AttributeError:
        pass
    return data, info


def read_cache_file(localfile):
    with open(localfile, "rb") as f:
        return f.read()


def read_url_info_from_cache(url):
    cached_file = get_local_file_name_by_url(url)
    if not os.path.exists(cached_file):
        return {}
    info_file = cached_file + ".headers"
    with open(info_file, "r", encoding="utf8") as inf:
        return json.loads(inf.read())


def write_cache_file(localfile, info_file, info, data):
    with open(localfile, "wb") as f:
        f.write(data)

    if info is not None:
        with open(info_file, "w", encoding="utf8") as f:
            url_info = dict()
            if hasattr(info, "_headers"):
                url_info['headers'] = dict(info._headers)
            else:
                url_info['headers'] = dict()
            url_info['charset'] = info.get_content_charset()
            f.write(json.dumps(url_info, indent=4, ensure_ascii=False))
    return data



def save_download_file(filename):
    global FILE_CACHE_FOLDER
    logger = logging.getLogger("dlrobot_logger")
    download_folder = os.path.join(FILE_CACHE_FOLDER, "downloads")
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
    assert (os.path.exists(filename))
    with open(filename, "rb") as f:
        hashcode = hashlib.sha256(f.read()).hexdigest()
    extension = os.path.splitext(filename)[1]
    save_filename = os.path.join(download_folder, hashcode + extension)
    logger.debug("save file {} as {}".format(filename, save_filename))
    if os.path.exists(save_filename):
        logger.debug("replace existing {0}".format(save_filename))
        os.remove(save_filename)
    os.rename(filename, save_filename)
    return save_filename


def _url_to_cached_folder (url):
    local_path = unquote(url)
    if local_path.startswith('http://'):
        local_path = local_path[len('http://'):]
    if local_path.startswith('https://'):
        local_path = local_path[len('https://'):]
    local_path = local_path.replace('\\', '/') # must be the same to calc hashlib.md5, change it after hashlib.md5
    local_path = re.sub("[:&=?'\"+<>()*| ]", '_', local_path)
    local_path = unidecode(local_path)
    local_path = local_path.strip("/") #https:////files.sudrf.ru/1060/user/Prikaz_o_naznachenii_otvetstvennogo.pdf
    if len(local_path) > 100:
        local_path = local_path[0:100] + "_" + hashlib.md5(local_path.encode('latin',  errors="ignore")).hexdigest()
    local_path = os.path.normpath(local_path)
    return local_path


def get_local_file_name_by_url(url):
    global FILE_CACHE_FOLDER
    cached_file = os.path.join(FILE_CACHE_FOLDER, _url_to_cached_folder(url), "dlrobot_data")
    folder = os.path.dirname(cached_file)
    if not os.path.exists(folder):
        os.makedirs(folder)
    return cached_file


def download_with_cache(url):
    localfile = get_local_file_name_by_url(url)
    info_file = localfile + ".headers"
    if os.path.exists(localfile):
        data = read_cache_file(localfile)
    else:
        data, info = download_with_urllib(url)
        if len(data) == 0:
            return ""
        write_cache_file(localfile, info_file, info, data)

    return data


def convert_html_to_utf8(url, html_data):
    url_info = read_url_info_from_cache(url)
    encoding = url_info.get('charset')
    if encoding is None:
        match = re.search('charset=([^"\']+)', html_data.decode('latin', errors="ignore"))
        if match:
            encoding = match.group(1)
        else:
            raise ValueError('unable to find encoding')
    if encoding.lower().startswith('cp-'):
        encoding = 'cp' + encoding[3:]

    return html_data.decode(encoding, errors="ignore")


def get_extenstion_by_content_type(headers):
    content_type = headers.get('Content-Type', "text")
    content_disposition = headers.get('Content-Disposition')
    if content_disposition is not None:
        found = re.findall("filename\s*=\s*(.+)", content_disposition.lower())
        if len(found) > 0:
            filename = found[0].strip("\"")
            _, file_extension = os.path.splitext(filename)
            return file_extension

    if content_type.startswith("text"):
        return DEFAULT_HTML_EXTENSION
    elif content_type.startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
        return ".xlsx"
    elif content_type.startswith("application/vnd.openxmlformats-officedocument"):
        return ".docx"
    elif content_type.find("ms-word") != -1:
        return ".doc"
    elif content_type.startswith("application/msword"):
        return ".doc"
    elif content_type.startswith("application/rtf"):
        return ".rtf"
    elif content_type.startswith("application/excel"):
        return ".xls"
    elif content_type.startswith("application/vnd.ms-excel"):
        return ".xls"
    elif content_type.startswith("application/pdf"):
        return ".pdf"
    elif content_type.startswith("application/zip"):
        return ".zip"
    elif content_type.startswith("application/rss+xml"):
        return ".some_xml"
    elif content_type.startswith("application/xml"):
        return ".some_xml"
    elif content_type.startswith("application/"):
        return ".some_application_format"
    elif content_type.startswith("image/"):
        return ".some_image_format"
    elif content_type.startswith("audio/"):
        return ".some_audio_format"
    elif content_type.startswith("video/"):
        return ".some_video_format"
    else:
        return DEFAULT_HTML_EXTENSION


def get_file_extension_by_cached_url(url):
    for e in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        if url.lower().endswith(e):
            return e

    headers = read_url_info_from_cache(url).get('headers', {})
    return get_extenstion_by_content_type(headers)


def get_file_extension_by_url(url):
    headers = request_url_headers(url)
    ext = get_extenstion_by_content_type(headers)
    return ext



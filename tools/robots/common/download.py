import ssl
import sys
import urllib.parse
import urllib.request
import json
import re
import shutil
import requests
from urllib.parse import urlparse, quote, urlunparse
import hashlib
from collections import defaultdict
import logging

import os
from selenium import webdriver
import time
FILE_CACHE_FOLDER="cached"
ACCEPTED_DECLARATION_FILE_EXTENSIONS = {'.doc', '.pdf', '.docx', '.xls', '.xlsx', '.rtf', '.zip'}
DEFAULT_HTML_EXTENSION = ".html"


def is_html_contents(info):
    content_type = info.get('Content-Type', "text").lower()
    return content_type.startswith('text')


HEADER_CACHE = {}
HEADER_REQUEST_COUNT = defaultdict(int)

def get_url_headers (url):
    global HEADER_CACHE
    global HEADER_REQUEST_COUNT
    if url in HEADER_CACHE:
        return HEADER_CACHE[url]
    if HEADER_REQUEST_COUNT[url] > 3:
        raise Exception("too many times to get headers that caused exceptions")

    HEADER_REQUEST_COUNT[url] += 1
    logger = logging.getLogger("dlrobot_logger")
    logger.debug("\tget headers for " + url)
    res = requests.head(url).headers
    HEADER_CACHE[url] = res
    return res


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
    o = list(urlparse(url)[:])
    if o[2].find('%') == -1:
        o[2] = quote(o[2])
    if has_cyrillic(o[1]):
        o[1] = o[1].encode('idna').decode('latin')
    url = urlunparse(o)
    context = ssl._create_unverified_context()
    req = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
    )
    data = ''
    info = {}
    headers = None
    logger = logging.getLogger("dlrobot_logger")
    logger.debug("urllib.request.urlopen ({})".format(url))
    with urllib.request.urlopen(req, context=context, timeout=20.0) as request:
        data = request.read()
        info = request.info()
        headers = request.headers

    try:
        if is_html_contents(info):
            logger.debug("\tencoding..")
            encoding = headers.get_content_charset()
            if encoding == None:
                match = re.search('charset=([^"\']+)', data.decode('latin', errors="ignore"))
                if match:
                    encoding = match.group(1)
                else:
                    raise ValueError('unable to find encoding')

            data = data.decode(encoding, errors="ignore")
            if search_for_js_redirect:
                try:
                    redirect_url = find_simple_js_redirect(data)
                    if redirect_url is not None and redirect_url != url:
                        return download_with_urllib(redirect_url, search_for_js_redirect=False)
                except Exception:
                    pass

    except AttributeError:
        pass
    return data, info


def read_cache_file(localfile, info_file):
    is_binary = False
    with open(info_file, "r", encoding="utf8") as inf:
        info = json.loads(inf.read())
        cached_headers = info['headers']
        is_binary = not is_html_contents(cached_headers)
    if is_binary:
        with open(localfile, "rb") as f:
            return f.read()
    else:
        with open(localfile, encoding="utf8") as f:
            return f.read()


def write_cache_file(localfile, info_file, info, data):
    if is_html_contents(info):
        with open(localfile, "w", encoding="utf8") as f:
            f.write(data)
    else:
        with open(localfile, "wb") as f:
            f.write(data)

    if info is not None:
        with open(info_file, "w", encoding="utf8") as f:
            headers_and_url = dict()
            if hasattr(info, "_headers"):
                headers_and_url['headers'] = dict(info._headers)
            else:
                headers_and_url['headers'] = dict()
            f.write(json.dumps(headers_and_url, indent=4, ensure_ascii=False))
    return data


def url_to_localfilename (url):
    localfile = url
    if localfile.startswith('http://'):
        localfile = localfile[7:]
    if localfile.startswith('https://'):
        localfile = localfile[8:]
    localfile = localfile.replace(':', '_')
    localfile = localfile.replace('/', '\\')
    localfile = localfile.replace('&', '_')
    localfile = localfile.replace('=', '_')
    localfile = localfile.replace('?', '_')
    if len(localfile) > 64:
        localfile = localfile[0:64] + "_" + hashlib.md5(url.encode('utf8',  errors="ignore")).hexdigest()
    return localfile



def save_download_file(filename):
    global FILE_CACHE_FOLDER
    download_folder = os.path.join(FILE_CACHE_FOLDER, "downloads")
    if not os.path.exists(download_folder):
        os.mkdir(download_folder)
    assert (os.path.exists(filename))
    hashcode = ""
    with open(filename, "rb") as f:
        hashcode = hashlib.sha256(f.read()).hexdigest()
    extension = os.path.splitext(filename)[1]
    save_filename = os.path.join(download_folder, hashcode + extension)
    if os.path.exists(save_filename):
        logger = logging.getLogger("dlrobot_logger")
        logger.debug("replace existing {0}".format(save_filename))
        os.remove(save_filename)
    os.rename(filename, save_filename)
    return save_filename

def get_local_file_name_by_url(url):
    global FILE_CACHE_FOLDER
    if not os.path.exists(FILE_CACHE_FOLDER):
        os.mkdir(FILE_CACHE_FOLDER)

    localfile = url_to_localfilename(url)

    localfile = os.path.join(FILE_CACHE_FOLDER, localfile)
    if not localfile.endswith('html') and not localfile.endswith('htm'):
        localfile += "/index.html"
    if not os.path.exists(os.path.dirname(localfile)):
        os.makedirs(os.path.dirname(localfile))
    return localfile


def download_with_cache(url):
    localfile = get_local_file_name_by_url(url)
    info_file = localfile + ".headers"
    if os.path.exists(localfile):
        return read_cache_file(localfile, info_file)
    else:
        data, info = download_with_urllib(url)
        if len(data) == 0:
            return ""
        write_cache_file(localfile, info_file, info, data)
        return data


def download_and_cache_with_selenium (url):
    browser = webdriver.Firefox()
    browser.minimize_window()
    browser.get(url)
    time.sleep(10)
    html = browser.page_source
    browser.close()
    browser.quit()
    return html


def download_page_collection(offices, page_collection_name):
    for office_info in offices:
        pages_to_download  = office_info.get(page_collection_name, dict()).get('links', dict())
        for url in pages_to_download:
            try:
                if 'downloaded_file' not in pages_to_download[url]:
                    download_with_cache(url)
            except Exception as err:
                sys.stderr.write("cannot download " + url + ": " + str(err) + "\n")
                pass

def get_extenstion_by_content_type(content_type):
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
        return ".xml"
    elif content_type.startswith("application/xml"):
        return ".xml"
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

    localfile = get_local_file_name_by_url(url)
    if not os.path.exists(localfile):
        return DEFAULT_HTML_EXTENSION

    info_file = localfile + ".headers"
    with open(info_file, "r", encoding="utf8") as inf:
        info = json.loads(inf.read())
        content_type = info['headers'].get('Content-Type', "text")

    return get_extenstion_by_content_type(content_type)


def get_file_extension_by_url(url):
    headers = get_url_headers(url)
    ext = get_extenstion_by_content_type(headers.get('Content-Type', "text"))
    return ext

def get_all_sha256(office_info, page_collection_name):
    pages_to_download = office_info.get(page_collection_name, dict()).get('links', dict())
    result = set()
    for url in pages_to_download:
        infile = get_local_file_name_by_url(url)
        if os.path.exists(infile):
            with open(infile, "rb") as f:
                result.add (hashlib.sha256(f.read()).hexdigest())
    return result

def export_files_to_folder(offices, page_collection_name, outfolder, file_extensions=ACCEPTED_DECLARATION_FILE_EXTENSIONS):
    logger = logging.getLogger("dlrobot_logger")
    for office_info in offices:
        pages_to_download  = office_info.get(page_collection_name, dict()).get('links', dict())
        if len(pages_to_download) == 0:
            continue
        office_folder = url_to_localfilename(list(office_info['morda']['links'].keys())[0])
        office_folder = os.path.join(outfolder, office_folder)
        if os.path.exists(office_folder):
            shutil.rmtree(office_folder)
        index = 0
        uniq_files = set()
        export_files = list()
        for url in pages_to_download:
            downloaded_file = pages_to_download[url].get('downloaded_file')
            if downloaded_file is not None:
                infile = downloaded_file
                extension = os.path.splitext(infile)[1]
            else:
                extension = get_file_extension_by_cached_url(url)
                infile = get_local_file_name_by_url(url)

            outpath = os.path.join(office_folder, str(index) + extension)
            if not os.path.exists(os.path.dirname(outpath)):
                os.makedirs(os.path.dirname(outpath))
            if os.path.exists(infile) and extension in file_extensions:
                sha256hash = ""
                with open(infile, "rb") as f:
                    sha256hash = hashlib.sha256(f.read()).hexdigest();
                if sha256hash not in uniq_files:
                    uniq_files.add(sha256hash)
                    shutil.copyfile(infile, outpath)
                    export_files.append((url, outpath))
                    index += 1
        office_info['exported_files'] = export_files
        logger.info("exported {0} files to {1}".format(index, office_folder))

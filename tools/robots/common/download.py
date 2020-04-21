import json
import re
from urllib.parse import urlparse, unquote
import hashlib
import logging
from unidecode import unidecode
import os
from robots.common.http_request import make_http_request, request_url_headers
from ConvStorage.conversion_client import on_save_file
from robots.common.content_types import  ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_HTML_EXTENSION
FILE_CACHE_FOLDER = "cached"


def is_html_contents(info):
    content_type = info.get('Content-Type', "text").lower()
    return content_type.startswith('text')


def find_simple_js_redirect(data):
    res = re.search('((window|document).location\s*=\s*[\'"]?)([^"\']+)([\'"]?\s*;)', data)
    if res:
        url = res.group(3)
        return url
    return Non


def get_site_domain_wo_www(url):
    url = "http://" + url.split("://")[-1]
    domain = urlparse(url).netloc
    if domain.startswith('www.'):
        domain = domain[len('www.'):]
    return domain




def http_get_with_urllib(url, search_for_js_redirect=True):
    info, headers, data = make_http_request(url, "GET")

    try:
        if is_html_contents(info):
            if search_for_js_redirect:
                try:
                    redirect_url = find_simple_js_redirect(data.decode('latin', errors="ignore"))
                    if redirect_url is not None and redirect_url != url:
                        return http_get_with_urllib(redirect_url, search_for_js_redirect=False)
                except Exception as err:
                    pass

    except AttributeError:
        pass
    return data, info


def read_cache_file(local_file):
    with open(local_file, "rb") as f:
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
    assert info is not None
    url_info = dict()
    if hasattr(info, "_headers"):
        url_info['headers'] = dict(info._headers)
    else:
        url_info['headers'] = dict()
    url_info['charset'] = info.get_content_charset()
    with open(info_file, "w", encoding="utf8") as f:
        f.write(json.dumps(url_info, indent=4, ensure_ascii=False))
    file_extension = get_file_extension_by_content_type(url_info['headers'])
    on_save_file(localfile, file_extension)
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
    file_extension = os.path.splitext(filename)[1]
    saved_filename = os.path.join(download_folder, hashcode + file_extension)
    logger.debug("save file {} as {}".format(filename, saved_filename))
    if os.path.exists(saved_filename):
        logger.debug("replace existing {0}".format(saved_filename))
        os.remove(saved_filename)
    os.rename(filename, saved_filename)
    on_save_file(saved_filename, file_extension)
    return saved_filename


def _url_to_cached_folder (url):
    local_path = unquote(url)
    if local_path.startswith('http://'):
        local_path = local_path[len('http://'):]
    if local_path.startswith('https://'):
        local_path = local_path[len('https://'):]
    local_path = local_path.replace('\\', '/') # must be the same to calc hashlib.md5, change it after hashlib.md5
    local_path = unidecode(local_path)
    local_path = re.sub("[:&=?'\"+<>()*| ]", '_', local_path)
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


def read_from_cache_or_download(url):
    local_file = get_local_file_name_by_url(url)
    info_file = local_file + ".headers"
    if os.path.exists(local_file):
        data = read_cache_file(local_file)
    else:
        data, info = http_get_with_urllib(url)
        if len(data) == 0:
            return ""
        write_cache_file(local_file, info_file, info, data)

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


def get_file_extension_by_content_type(headers):
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
    return get_file_extension_by_content_type(headers)


def get_file_extension_by_url(url):
    headers = request_url_headers(url)
    ext = get_file_extension_by_content_type(headers)
    return ext



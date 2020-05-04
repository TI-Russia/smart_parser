import json
import re
import urllib.parse
import urllib.error
import hashlib
import logging
from unidecode import unidecode
import os
import shutil
from robots.common.http_request import make_http_request, request_url_headers
from robots.common.content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_HTML_EXTENSION
from ConvStorage.conversion_client import TDocConversionClient
from bs4 import BeautifulSoup

class TDownloadEnv:
    FILE_CACHE_FOLDER = "cached"
    CONVERSION_CLIENT = None

    @staticmethod
    def clear_cache_folder():
        if os.path.exists(TDownloadEnv.FILE_CACHE_FOLDER):
            shutil.rmtree(TDownloadEnv.FILE_CACHE_FOLDER, ignore_errors=True)
        if not os.path.exists(TDownloadEnv.FILE_CACHE_FOLDER):
            os.mkdir(TDownloadEnv.FILE_CACHE_FOLDER)

    @staticmethod
    def init_conversion():
        TDownloadEnv.CONVERSION_CLIENT = TDocConversionClient()
        TDownloadEnv.CONVERSION_CLIENT.start_conversion_thread()


def is_html_contents(info):
    content_type = info.get('Content-Type', "text").lower()
    return content_type.startswith('text')


def find_simple_js_redirect(data):
    res = re.search('((window|document).location\s*=\s*[\'"]?)([^"\'\s]+)([\'"]?\s*;)', data)
    if res:
        url = res.group(3)
        return url
    return None


def convert_html_to_utf8_using_content_charset(content_charset, html_data):
    if content_charset is not None:
        encoding = content_charset
    else: # todo: use BeautifulSoup here
        match = re.search('charset\s*=\s*"?([^"\']+)', html_data.decode('latin', errors="ignore"))
        if match:
            encoding = match.group(1).strip()
        else:
            raise ValueError('unable to find encoding')
    if encoding.lower().startswith('cp-'):
        encoding = 'cp' + encoding[3:]

    return html_data.decode(encoding, errors="ignore")


def convert_html_to_utf8(url, html_data):
    url_info = read_url_info_from_cache(url)
    return convert_html_to_utf8_using_content_charset(url_info.get('charset'), html_data)


def http_get_with_urllib(url, search_for_js_redirect=True):
    redirected_url, headers, data = make_http_request(url, "GET")

    try:
        if is_html_contents(headers):
            if search_for_js_redirect:
                try:
                    data_utf8 = convert_html_to_utf8_using_content_charset(headers.get_content_charset(), data)
                    redirect_url = find_simple_js_redirect(data_utf8)
                    if redirect_url is not None and redirect_url != url:
                        return http_get_with_urllib(redirect_url, search_for_js_redirect=False)
                except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as err:
                    pass

    except AttributeError:
        pass
    return data, headers


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


# file downloaded by urllib
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
    if TDownloadEnv.CONVERSION_CLIENT is not None:
        TDownloadEnv.CONVERSION_CLIENT.start_conversion_task_if_needed(localfile, file_extension)
    return data


# save from selenium
def save_downloaded_file(filename):
    logger = logging.getLogger("dlrobot_logger")
    download_folder = os.path.join(TDownloadEnv.FILE_CACHE_FOLDER, "downloads")
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
    if TDownloadEnv.CONVERSION_CLIENT is not None:
        TDownloadEnv.CONVERSION_CLIENT.start_conversion_task_if_needed(saved_filename, file_extension)
    return saved_filename


def _url_to_cached_folder_verbose(url):
    local_path = urllib.parse.unquote(url)
    if local_path.startswith('http://'):
        local_path = local_path[len('http://'):]
    if local_path.startswith('https://'):
        local_path = local_path[len('https://'):]
    local_path = local_path.replace('\\', '/') # must be the same to calc hashlib.md5, change it after hashlib.md5
    local_path = re.sub('/\\.+/', '/q/', local_path)  # dots are interpreted as to go to the parent folder  (cd ..)
    local_path = unidecode(local_path)
    local_path = re.sub("[#:&=?'\"+<>()*| ]", '_', local_path)
    local_path = local_path.strip("/") #https:////files.sudrf.ru/1060/user/Prikaz_o_naznachenii_otvetstvennogo.pdf
    if len(local_path) > 100:
        local_path = local_path[0:100] + "_" + hashlib.md5(local_path.encode('latin',  errors="ignore")).hexdigest()
    local_path = os.path.normpath(local_path)
    return local_path


def get_local_file_name_by_url(url):
    folder = os.path.join(TDownloadEnv.FILE_CACHE_FOLDER, _url_to_cached_folder_verbose(url))
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)
    except FileNotFoundError as exp:
        #logging.getLogger("dlrobot_logger").error("cannot create verbose path for {}, hash it".format(url))
        hashcode = hashlib.sha256(url.encode('latin', errors="ignore")).hexdigest()
        folder = os.path.join(TDownloadEnv.FILE_CACHE_FOLDER, hashcode)
    return os.path.join(folder, "dlrobot_data")


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


def get_file_extension_by_content_type(headers):
    content_type = headers.get('Content-Type', headers.get('Content-type', "text"))
    content_disposition = headers.get('Content-Disposition')
    if content_disposition is not None:
        found = re.findall("filename\s*=\s*(.+)", content_disposition.lower())
        if len(found) > 0:
            filename = found[0].strip("\"")
            _, file_extension = os.path.splitext(filename)
            return file_extension

    if content_type.startswith("text/csv"):
        return ".csv"
    elif content_type.startswith("text/css"):
        return ".css"
    elif content_type.startswith("text/javascript"):
        return ".js"
    elif content_type.startswith("text/plain"):
        return ".txt"
    elif content_type.startswith("text/xml"):
        return ".xml"
    elif content_type.startswith("text"):
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
    local_file = get_local_file_name_by_url(url)
    if os.path.exists(local_file):  #can be 404, do not try to fetch it
        data_start = read_cache_file(local_file).decode('latin', errors="ignore").strip(" \r\n\t")[0:100]
        data_start = data_start.lower().replace(" ", "")
        if data_start.startswith("<html") or data_start.startswith("<docttypehtml") \
                or data_start.startswith("<!docttypehtml"):
            return DEFAULT_HTML_EXTENSION

    for e in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        if url.lower().endswith(e):
            return e

    headers = read_url_info_from_cache(url).get('headers', {})
    return get_file_extension_by_content_type(headers)


# use it preliminary, because ContentDisposition and Content-type often contain errors
def get_file_extension_only_by_headers(url):
    _, headers = request_url_headers(url)
    ext = get_file_extension_by_content_type(headers)
    return ext


def request_url_title(url):
    try:
        html = read_from_cache_or_download(url)
        if get_file_extension_by_cached_url(url) == DEFAULT_HTML_EXTENSION:
            soup = BeautifulSoup(html, "html.parser")
            return soup.title.string.strip(" \n\r\t")
    except Exception as err:
        return ""


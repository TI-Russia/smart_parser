import json
import re
import urllib.parse
import urllib.error
import hashlib
import logging
from unidecode import unidecode
import os
import shutil
from robots.common.http_request import make_http_request, request_url_headers_with_global_cache
from robots.common.content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_HTML_EXTENSION
from ConvStorage.conversion_client import TDocConversionClient
from robots.common.http_request import RobotHttpException
import cgi


class TDownloadEnv:
    FILE_CACHE_FOLDER = "cached"
    CONVERSION_CLIENT = None
    HTTP_TIMEOUT = 30

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

    @staticmethod
    def send_pdf_to_conversion(filename, file_extension):
        if TDownloadEnv.CONVERSION_CLIENT is None:
            return
        if TDownloadEnv.CONVERSION_CLIENT.all_pdf_size_sent_to_conversion < 50 * 2**20:
            # no sense to send more than 50 Mb, other clients will suffer
            TDownloadEnv.CONVERSION_CLIENT.start_conversion_task_if_needed(filename, file_extension)

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


def get_content_type_from_headers(headers, default_value="text"):
    return headers.get('Content-Type', headers.get('Content-type', headers.get('content-type', default_value)))


def get_content_charset(headers):
    if hasattr(headers, "_headers"):
        # from urllib, headers is class Message
        return headers.get_content_charset()
    else:
        # from curl, headers is a dict
        content_type = get_content_type_from_headers(headers).lower()
        _, params = cgi.parse_header(content_type)
        return params.get('charset')


def http_get_request_with_simple_js_redirect(logger, url):
    redirected_url, headers, data = make_http_request(logger, url, "GET", timeout=TDownloadEnv.HTTP_TIMEOUT)

    try:
        if get_content_type_from_headers(headers).lower().startswith('text'):
            try:
                data_utf8 = convert_html_to_utf8_using_content_charset(get_content_charset(headers), data)
                match = re.search('((window|document).location\s*=\s*[\'"]?)([^"\'\s]+)([\'"]?\s*;)', data_utf8)
                if match:
                    redirect_url = match.group(3)
                    if redirect_url != url:
                        return make_http_request(logger, redirect_url, "GET", timeout=TDownloadEnv.HTTP_TIMEOUT)
            except (RobotHttpException, ValueError) as err:
                pass
    except AttributeError:
        pass
    return redirected_url, headers, data


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
    TDownloadEnv.send_pdf_to_conversion(saved_filename, file_extension)
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
        hashcode = hashlib.sha256(url.encode('latin', errors="ignore")).hexdigest()
        folder = os.path.join(TDownloadEnv.FILE_CACHE_FOLDER, hashcode)
        if not os.path.exists(folder):
            os.makedirs(folder)
    return os.path.join(folder, "dlrobot_data")


def get_file_extension_by_content_type(headers):
    content_type = get_content_type_from_headers(headers)
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


class TDownloadedFile:
    def get_page_info_file_name(self):
        return self.data_file_path + ".page_info"

    def __init__(self, original_url, download_if_absent=True):
        self.original_url = original_url
        self.page_info = dict()
        self.data_file_path = get_local_file_name_by_url(self.original_url)
        self.data = ""
        self.file_extension = None
        if os.path.exists(self.data_file_path):
            with open(self.data_file_path, "rb") as f:
                self.data = f.read()
            with open(self.get_page_info_file_name(), "r", encoding="utf8") as f:
                self.page_info = json.loads(f.read())
            self.redirected_url = self.page_info.get('redirected_url', self.original_url)
            self.file_extension = self.page_info.get('file_extension')
        else:
            logger = logging.getLogger("dlrobot_logger")
            redirected_url, info, data = http_get_request_with_simple_js_redirect(logger, original_url)
            self.redirected_url = redirected_url
            self.data = data
            if hasattr(info, "_headers"):
                self.page_info['headers'] = dict(info._headers)
            else:
                assert type(info) == dict
                self.page_info['headers'] = info
            self.page_info['charset'] = get_content_charset(info)
            self.page_info['redirected_url'] = redirected_url
            self.page_info['original_url'] = original_url
            if len(self.data) > 0:
                self.file_extension = self.calc_file_extension_by_data_and_headers()
                self.page_info['file_extension'] = self.file_extension
                self.write_file_to_cache()
                TDownloadEnv.send_pdf_to_conversion(self.data_file_path, self.file_extension)

    def write_file_to_cache(self):
        with open(self.data_file_path, "wb") as f:
            f.write(self.data)
        with open(self.get_page_info_file_name(), "w", encoding="utf8") as f:
            f.write(json.dumps(self.page_info, indent=4, ensure_ascii=False))

    def convert_html_to_utf8(self):
        return convert_html_to_utf8_using_content_charset(self.page_info.get('charset'), self.data)

    def get_http_headers(self):
        return self.page_info.get('headers', dict())

    def calc_file_extension_by_data_and_headers(self):
        if len(self.data) > 0:  # can be 404, do not try to fetch it
            data_start = self.data.decode('latin', errors="ignore").strip(" \r\n\t")[0:100]
            data_start = data_start.lower().replace(" ", "")
            if data_start.startswith("<html") or data_start.startswith("<docttypehtml") \
                    or data_start.startswith("<!docttypehtml"):
                return DEFAULT_HTML_EXTENSION

        for e in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
            if self.original_url.lower().endswith(e):
                return e

        return get_file_extension_by_content_type(self.get_http_headers())

    def get_file_extension_only_by_headers(self):
        return get_file_extension_by_content_type(self.get_http_headers())


# use it preliminary, because ContentDisposition and Content-type often contain errors
def get_file_extension_only_by_headers(url):
    logger = logging.getLogger("dlrobot_logger")
    _, headers = request_url_headers_with_global_cache(logger, url)
    ext = get_file_extension_by_content_type(headers)
    return ext


def are_web_mirrors(domain1, domain2):
    try:
        # check all mirrors including simple javascript
        html1 = TDownloadedFile(domain1).data
        html2 = TDownloadedFile(domain2).data
        res = len(html1) == len(html2)  # it is enough
        return res
    except RobotHttpException as exp:
        return False

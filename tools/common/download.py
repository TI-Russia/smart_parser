from common.http_request import THttpRequester
from common.content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_HTML_EXTENSION, \
    file_extension_by_file_contents

from ConvStorage.conversion_client import TDocConversionClient
from common.primitives import build_dislosures_sha256, build_dislosures_sha256_by_file_data
from common.html_parser import THtmlParser

import json
import re
import urllib.parse
import urllib.error
import hashlib
from unidecode import unidecode
import os
import shutil
import cgi


class TDownloadEnv:
    FILE_CACHE_FOLDER = "cached"
    CONVERSION_CLIENT: TDocConversionClient = None
    PDF_QUOTA_CONVERSION = 20 * 2**20 # in bytes

    @staticmethod
    def get_download_folder():
        return os.path.join(TDownloadEnv.FILE_CACHE_FOLDER, "downloads")

    @staticmethod
    def clear_cache_folder():
        if os.path.exists(TDownloadEnv.FILE_CACHE_FOLDER):
            shutil.rmtree(TDownloadEnv.FILE_CACHE_FOLDER, ignore_errors=True)
        if not os.path.exists(TDownloadEnv.FILE_CACHE_FOLDER):
            try:
                os.mkdir(TDownloadEnv.FILE_CACHE_FOLDER)
            except Exception as exp:
                print("cannot create folder {}, cwd={}".format(TDownloadEnv.FILE_CACHE_FOLDER, os.getcwd()))
                raise

    @staticmethod
    def init_conversion(logger):
        TDownloadEnv.CONVERSION_CLIENT = TDocConversionClient(TDocConversionClient.parse_args([]), logger=logger)
        TDownloadEnv.CONVERSION_CLIENT.start_conversion_thread()

    @staticmethod
    def get_search_engine_cache_folder():
        d = os.path.join(TDownloadEnv.FILE_CACHE_FOLDER, "search_engine_requests")
        if not os.path.exists(d):
            os.makedirs(d)
        return d

    @staticmethod
    def send_pdf_to_conversion(filename, file_extension, sha256):
        if TDownloadEnv.CONVERSION_CLIENT is None:
            return
        if not TDownloadEnv.CONVERSION_CLIENT.is_acceptable_file_extension(file_extension):
            return
        TDownloadEnv.CONVERSION_CLIENT.logger.debug('got pdf or archive with sha256={})'.format(sha256))
        if TDownloadEnv.CONVERSION_CLIENT.all_pdf_size_sent_to_conversion < TDownloadEnv.PDF_QUOTA_CONVERSION:
            TDownloadEnv.CONVERSION_CLIENT.start_conversion_task_if_needed(filename, file_extension)
        else:
            TDownloadEnv.CONVERSION_CLIENT.logger.debug('skip sending a pdf to conversion (sum sent size exceeds {})'.format(
                TDownloadEnv.PDF_QUOTA_CONVERSION))


def get_original_encoding(content_charset, html_data):
    if content_charset is not None:
        encoding = content_charset
        if encoding.lower().startswith('cp-'):
            encoding = 'cp' + encoding[3:]
        return encoding
    else:
        latin_encoded = html_data.decode('latin', errors="ignore").lower()
        match = re.search('charset\s*=\s*"?([^"\'>]+)', latin_encoded)
        if match:
            encoding = match.group(1).strip()
            if encoding.lower().startswith('cp-'):
                encoding = 'cp' + encoding[3:]
            return encoding
        else:
            if latin_encoded[0:500].find('utf') != -1:
                return "utf8"
            elif latin_encoded[0:500].find('windows-1251') != -1:
                return "windows-1251"
            elif latin_encoded[0:500].find('koi8-r') != -1:
                return "koi8-r"
            else:
                # very slow
                parser = THtmlParser(html_data)
                return parser.soup.original_encoding


def get_content_charset(headers):
    if hasattr(headers, "_headers"):
        # from urllib, headers is class Message
        return headers.get_content_charset()
    else:
        # from curl, headers is a dict
        content_type = THttpRequester.get_content_type_from_headers(headers).lower()
        _, params = cgi.parse_header(content_type)
        return params.get('charset')


# save from selenium download folder (via javascript, unknown target_url)
def save_downloaded_file(filename):
    download_folder = TDownloadEnv.get_download_folder()
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
    assert (os.path.exists(filename))
    sha256 = build_dislosures_sha256(filename)
    file_extension = os.path.splitext(filename)[1]
    if file_extension == '':
        file_extension = file_extension_by_file_contents(filename)
    saved_filename = os.path.join(download_folder, sha256 + file_extension)
    if THttpRequester.logger is not None:
        THttpRequester.logger.debug("save file {} as {}".format(filename, saved_filename))
    if os.path.exists(saved_filename):
        if THttpRequester.logger is not None:
            THttpRequester.logger.debug("replace existing {0}".format(saved_filename))
        os.remove(saved_filename)
    os.rename(filename, saved_filename)
    TDownloadEnv.send_pdf_to_conversion(saved_filename, file_extension, sha256)
    return saved_filename


def _url_to_cached_folder_verbose(url):
    local_path = urllib.parse.unquote(url)
    if local_path.startswith('http://'):
        local_path = local_path[len('http://'):]
    if local_path.startswith('https://'):
        local_path = local_path[len('https://'):] + "_s"
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


class TDownloadedFile:
    def get_page_info_file_name(self):
        return self.data_file_path + ".page_info"

    def __init__(self, original_url, use_cache=True):
        self.logger = THttpRequester.logger
        self.original_url = original_url
        self.page_info = dict()
        self.data_file_path = get_local_file_name_by_url(self.original_url)
        self.data = ""
        self.file_extension = None
        self.redirected_url = None
        self.timeout = THttpRequester.DEFAULT_HTTP_TIMEOUT
        if use_cache and os.path.exists(self.data_file_path):
            self.load_from_cached_file()
        else:
            self.download_from_remote_server()

    def load_from_cached_file(self):
        with open(self.data_file_path, "rb") as f:
            self.data = f.read()
        with open(self.get_page_info_file_name(), "r", encoding="utf8") as f:
            self.page_info = json.loads(f.read())
        self.redirected_url = self.page_info.get('redirected_url', self.original_url)
        self.file_extension = self.page_info.get('file_extension')

    def download_from_remote_server(self):
        ext = get_file_extension_only_by_headers(self.original_url)
        if ext != DEFAULT_HTML_EXTENSION:
            self.timeout = 120
            self.logger.debug("use http timeout {}".format(self.timeout))

        self.redirected_url, headers, self.data = THttpRequester.make_http_request(self.original_url, "GET", self.timeout)

        if hasattr(headers, "_headers"):
            self.page_info['headers'] = dict(headers._headers)
        else:
            assert type(headers) == dict
            self.page_info['headers'] = headers
        self.page_info['charset_by_headers'] = get_content_charset(headers)
        self.page_info['redirected_url'] = self.redirected_url
        self.page_info['original_url'] = self.original_url
        if len(self.data) > 0:
            self.file_extension = self.calc_file_extension_by_data_and_headers()
            self.page_info['file_extension'] = self.file_extension
            self.page_info['sha256'] = build_dislosures_sha256_by_file_data(self.data, self.file_extension)
            if self.file_extension == DEFAULT_HTML_EXTENSION:
                self.page_info['original_encoding'] = get_original_encoding(self.page_info.get('charset_by_headers'), self.data)
            self.write_file_to_cache()
            TDownloadEnv.send_pdf_to_conversion(self.data_file_path, self.file_extension, self.page_info['sha256'])

    def get_sha256(self):
        return self.page_info['sha256']

    def write_file_to_cache(self):
        with open(self.data_file_path, "wb") as f:
            f.write(self.data)
        with open(self.get_page_info_file_name(), "w", encoding="utf8") as f:
            f.write(json.dumps(self.page_info, indent=4, ensure_ascii=False))

    def convert_html_to_utf8(self):
        try:
            return self.data.decode(self.page_info['original_encoding'], errors="ignore")
        except Exception as exp:
            raise ValueError('unable to find encoding')

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

        return THttpRequester.get_file_extension_by_content_type(self.get_http_headers())

    def get_file_extension_only_by_headers(self):
        return THttpRequester.get_file_extension_by_content_type(self.get_http_headers())


# use it preliminary, because ContentDisposition and Content-type often contain errors
def get_file_extension_only_by_headers(url):
    try:
        # think that www.example.com/aaa/aa is always an html
        _, headers = THttpRequester.request_url_headers_with_global_cache(url)
        ext = THttpRequester.get_file_extension_by_content_type(headers)
        return ext
    except THttpRequester.RobotHttpException as err:
        return None


# use it preliminary, because ContentDisposition and Content-type often contain errors
def get_file_size_by_http_headers(url):
    _, headers = THttpRequester.request_url_headers_with_global_cache(url)
    len = headers.get('content-length', headers.get('Content-Length', 0))
    return int(len)


def have_the_same_content_length(url1, url2):
    try:
        len1 = get_file_size_by_http_headers(url1)
        len2 = get_file_size_by_http_headers(url2)
        return len1 == len2 and len1 > 0  # these urls are hyperlinked, so it is enough
    except THttpRequester.RobotHttpException as exp:
        return False


def have_the_same_html(url1, url2):
    try:
        # check all mirrors including simple javascript
        html1 = TDownloadedFile(url1).data
        html2 = TDownloadedFile(url2).data
        res = len(html1) == len(html2)  # it is enough
        return res
    except THttpRequester.RobotHttpException as exp:
        return False


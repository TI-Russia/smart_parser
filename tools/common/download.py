from common.http_request import THttpRequester
from common.content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_HTML_EXTENSION, \
    file_extension_by_file_contents

from ConvStorage.conversion_client import TDocConversionClient
from common.primitives import build_dislosures_sha256

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
    LAST_CONVERSION_TIMEOUT = 30*60  # in seconds
    PDF_QUOTA_CONVERSION = 20 * 2**20 # in bytes
    logger = None

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
        TDownloadEnv.logger = logger
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


def convert_html_to_utf8_using_content_charset(content_charset, html_data):
    if content_charset is not None:
        encoding = content_charset
    else: # todo: use BeautifulSoup here
        match = re.search('charset\s*=\s*"?([^"\'>]+)', html_data.decode('latin', errors="ignore"))
        if match:
            encoding = match.group(1).strip()
        else:
            raise ValueError('unable to find encoding')
    if encoding.lower().startswith('cp-'):
        encoding = 'cp' + encoding[3:]
    try:
        encoded_data = html_data.decode(encoding, errors="ignore")
        return encoded_data
    except Exception as exp:
        raise ValueError('unable to find encoding')


def get_content_charset(headers):
    if hasattr(headers, "_headers"):
        # from urllib, headers is class Message
        return headers.get_content_charset()
    else:
        # from curl, headers is a dict
        content_type = THttpRequester.get_content_type_from_headers(headers).lower()
        _, params = cgi.parse_header(content_type)
        return params.get('charset')


# save from selenium
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
    if TDownloadEnv.logger is not None:
        TDownloadEnv.logger.debug("save file {} as {}".format(filename, saved_filename))
    if os.path.exists(saved_filename):
        if TDownloadEnv.logger is not None:
            TDownloadEnv.logger.debug("replace existing {0}".format(saved_filename))
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

    def __init__(self, original_url):
        self.logger = TDownloadEnv.logger
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
            redirected_url, headers, data = self._http_get_request_with_simple_js_redirect()
            self.redirected_url = redirected_url
            self.data = data
            if hasattr(headers, "_headers"):
                self.page_info['headers'] = dict(headers._headers)
            else:
                assert type(headers) == dict
                self.page_info['headers'] = headers
            self.page_info['charset'] = get_content_charset(headers)
            self.page_info['redirected_url'] = redirected_url
            self.page_info['original_url'] = original_url
            if len(self.data) > 0:
                self.file_extension = self.calc_file_extension_by_data_and_headers()
                self.page_info['file_extension'] = self.file_extension
                self.write_file_to_cache()
                sha256 = hashlib.sha256(data).hexdigest()
                TDownloadEnv.send_pdf_to_conversion(self.data_file_path, self.file_extension, sha256)

    @staticmethod
    def get_simple_js_redirect(main_url, data_utf8):
        match = re.search('\n[^=]*((window|document).location(.href)?\s*=\s*[\'"]?)([^"\'\s]+)([\'"]?\s*;)', data_utf8)
        if match:
            redirect_url = match.group(4)
            if redirect_url.startswith('http'):
                return redirect_url

            # the "else" is too dangerous (see "window.location = a.href;" in http://батайск-официальный.рф)
            #else:
            #    return urllib.parse.urljoin(main_url, redirect_url)

        return None

    def _http_get_request_with_simple_js_redirect(self):
        redirected_url, headers, data = THttpRequester.make_http_request(self.original_url, "GET")

        try:
            if THttpRequester.get_content_type_from_headers(headers).lower().startswith('text'):
                try:
                    data_utf8 = convert_html_to_utf8_using_content_charset(get_content_charset(headers), data)
                    redirect_url = self.get_simple_js_redirect(self.original_url, data_utf8)
                    if redirect_url is not None:
                        return THttpRequester.make_http_request(redirect_url, "GET")
                except (THttpRequester.RobotHttpException, ValueError) as err:
                    pass
        except AttributeError:
            pass
        return redirected_url, headers, data

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

        return THttpRequester.get_file_extension_by_content_type(self.get_http_headers())

    def get_file_extension_only_by_headers(self):
        return THttpRequester.get_file_extension_by_content_type(self.get_http_headers())


# use it preliminary, because ContentDisposition and Content-type often contain errors
def get_file_extension_only_by_headers(url):
    _, headers = THttpRequester.request_url_headers_with_global_cache(url)
    ext = THttpRequester.get_file_extension_by_content_type(headers)
    return ext


def are_mirrors_by_html(url1, url2):
    try:
        # check all mirrors including simple javascript
        html1 = TDownloadedFile(url1).data
        html2 = TDownloadedFile(url2).data
        res = len(html1) == len(html2)  # it is enough
        return res
    except THttpRequester.RobotHttpException as exp:
        return False

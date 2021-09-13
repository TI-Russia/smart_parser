
from common.content_types import content_type_to_file_extension, is_video_or_audio_file_extension
from common.urllib_parse_pro import TUrlUtf8Encode, urlsplit_pro

import ssl
import urllib3
import urllib.error
import urllib.request
import urllib.parse
from collections import defaultdict
import time
import datetime
import re
import sys
import json
import socket
import http.client
import os
import random
import pycurl
from io import BytesIO
import certifi

DLROBOT_CIPHERS_LIST =  os.environ.get("DLROBOT_CIPHERS", "DEFAULT@SECLEVEL=1")

urllib3.disable_warnings()
urllib3.util.ssl_.DEFAULT_CIPHERS += DLROBOT_CIPHERS_LIST #(':HIGH:!DH:!aNULL'



def get_user_agent():
    # два curl к https://minzdrav.gov.ru/special с этим user agent и IP забанен
    robot_user_agents = [
        "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; Linux x86_64; Mail.RU_Bot/2.0; +http://go.mail.ru/help/robots)"
    ]
    # admkumertau.ru responds only to "human" user agents
    human_user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 YaBrowser/21.6.0.616 Yowser/2.5 Safari/537.36'
    ]
    #return random.choice(robot_user_agents)
    return random.choice(human_user_agents)


def get_redirected_url_urllib3(response, original_url):
    redirected_url = response.geturl()
    if redirected_url is None:
        return original_url
    if redirected_url.startswith('http'):
        return redirected_url
    if response.retries is not None and len(response.retries.history):
        for i in range(1, len(response.retries.history)+1):
            history_url = response.retries.history[-i].redirect_location
            if history_url.startswith('http'):
                return urllib.parse.urljoin(history_url, redirected_url)
    return urllib.parse.urljoin(original_url, redirected_url)


class TCurlResponse:
    def __init__(self, url, method):
        self.method = method
        self.original_url = url
        self.headers = dict()
        self.last_full_redirected_url = None
        self.write_data = True
        self.first_write = True
        self.data = b''

    def get_redirected_url(self):
        if self.last_full_redirected_url is not None:
            return self.last_full_redirected_url
        else:
            return self.original_url

    def collect_http_headers(self, header_line):
        header_line = header_line.decode('iso-8859-1').strip()
        if header_line.startswith('HTTP/1') or header_line.startswith('HTTP/2'):
            self.headers = dict() # a redirect  occurs, forget all headers
        # Ignore all lines without a colon
        if ':' not in header_line:
            return

        # Break the header line into header name and value
        h_name, h_value = header_line.split(':', 1)

        # Remove whitespace that may be present
        h_name = h_name.strip()
        h_value = h_value.strip()
        h_name = h_name.lower() # Convert header names to lowercase
        self.headers[h_name] = h_value # Header name and value.
        if h_name.lower() == "location" and h_value.startswith('http'):
            self.last_full_redirected_url = h_value

    def write_callback(self, buffer):
        if self.first_write:
            self.first_write = False
            if self.method == "GET":
                file_ext = THttpRequester.get_file_extension_by_content_type(self.headers)
                if is_video_or_audio_file_extension(file_ext) and not THttpRequester.ENABLE_VIDEO_AND_AUDIO:
                    self.write_data = False
                    return 0
        if not self.write_data:
            return 0
        self.data += buffer
        return len(buffer)


class THttpRequester:
    DEFAULT_HTTP_TIMEOUT = 30  # in seconds
    ENABLE = True
    SECONDS_BETWEEN_HEAD_REQUESTS = 1.0
    REQUEST_RATE_1_MIN = 50
    REQUEST_RATE_10_MIN = 300
    ALL_HTTP_REQUEST = dict()  # (url, method) -> time
    HTTP_EXCEPTION_COUNTER = defaultdict(int)  # (url, method) -> number of exception
    HTTP_503_ERRORS_COUNT = 0
    SSL_CONTEXT = None
    #HTTP_LIB = os.environ.get("DLROBOT_HTTP_LIB", "urllib")
    HTTP_LIB = os.environ.get("DLROBOT_HTTP_LIB", "curl")
    logger = None
    LAST_HEAD_REQUEST_TIME = datetime.datetime.now()
    HEADER_MEMORY_CACHE = dict()
    WEB_PAGE_LINKS_PROCESSING_MAX_TIME = 60 * 20  # 20 minutes
    ENABLE_VIDEO_AND_AUDIO = False
    ENABLE_HEAD_REQUESTS = True

    @staticmethod
    def initialize(logger):
        THttpRequester.logger = logger
        THttpRequester.SSL_CONTEXT = ssl._create_unverified_context()
        THttpRequester.SSL_CONTEXT.set_ciphers(DLROBOT_CIPHERS_LIST)
        if os.environ.get("DLROBOT_HTTP_TIMEOUT"):
            THttpRequester.logger.info("set http timeout to {}".format(os.environ.get("DLROBOT_HTTP_TIMEOUT")))
            THttpRequester.DEFAULT_HTTP_TIMEOUT = int(os.environ.get("DLROBOT_HTTP_TIMEOUT"))

    # decrement HTTP_503_ERRORS_COUNT on successful http_request
    @staticmethod
    def register_successful_request():
        if THttpRequester.ENABLE:
            if THttpRequester.HTTP_503_ERRORS_COUNT > 0:
                THttpRequester.HTTP_503_ERRORS_COUNT -= 1  # decrement HTTP_503_ERRORS_COUNT on successful http_request

    @staticmethod
    def get_request_rate(min_time=0):
        current_time = time.time()
        time_points = list(t for t in THttpRequester.ALL_HTTP_REQUEST.values() if t > min_time)
        return {
            "request_rate_1_min": sum(1 for t in time_points if (current_time - t) < 60),
            "request_rate_10_min": sum(1 for t in time_points if (current_time - t) < 60 * 10),
            "request_count": len(time_points)
        }

    class RobotHttpException(Exception):
        def __init__(self, value, url, http_code, http_method):
            key = (url, http_method)
            if THttpRequester.ENABLE:
                THttpRequester.HTTP_EXCEPTION_COUNTER[key] = THttpRequester.HTTP_EXCEPTION_COUNTER[key] + 1
                self.count = THttpRequester.HTTP_EXCEPTION_COUNTER[key]
            else:
                self.count = 1
            self.value = value
            self.url = url
            self.http_code = http_code
            self.http_method = http_method

        def __str__(self):
            return "cannot make http-request ({}) to {} got code {}, initial exception: {}".format( \
                self.http_method, self.url, self.http_code, self.value)

    @staticmethod
    def deal_with_http_code_503():
        if not THttpRequester.ENABLE:
            return
        request_rates = THttpRequester.get_request_rate()
        THttpRequester.logger.error("got HTTP-503 got, request_rate={}".format(json.dumps(request_rates)))
        max_http_503_errors_count = 20
        THttpRequester.HTTP_503_ERRORS_COUNT += 1
        if THttpRequester.HTTP_503_ERRORS_COUNT > max_http_503_errors_count:
            THttpRequester.logger.error("full stop after {} HTTP-503 errors to prevent a possible ddos attack".format(
                max_http_503_errors_count))
            sys.exit(1)
        else:
            THttpRequester.logger.error("wait 1 minute after HTTP-503 N {}".format(THttpRequester.HTTP_503_ERRORS_COUNT))
            time.sleep(60)
            if THttpRequester.HTTP_503_ERRORS_COUNT + 1 > max_http_503_errors_count:
                THttpRequester.logger.error("last chance before exit, wait 20 minutes")
                time.sleep(20 * 60)

    @staticmethod
    def wait_until_policy_compliance(policy_name, max_policy_value):
        if not THttpRequester.ENABLE:
            return
        request_rates = THttpRequester.get_request_rate()
        sleep_sec = max_policy_value / 10
        while request_rates[policy_name] > max_policy_value:
            THttpRequester.logger.debug("wait {} seconds to comply {} (max value={})".format(sleep_sec, policy_name, max_policy_value))
            time.sleep(sleep_sec)
            request_rates = THttpRequester.get_request_rate()

    @staticmethod
    def consider_request_policy(url, method):
        if not THttpRequester.ENABLE:
            return

        if THttpRequester.HTTP_EXCEPTION_COUNTER[(url, method)] > 2:
            raise THttpRequester.RobotHttpException("stop requesting the same url", url, 429, method)

        if len(THttpRequester.ALL_HTTP_REQUEST) > 80:
            THttpRequester.wait_until_policy_compliance("request_rate_1_min", THttpRequester.REQUEST_RATE_1_MIN)
            THttpRequester.wait_until_policy_compliance("request_rate_10_min", THttpRequester.REQUEST_RATE_10_MIN)

        THttpRequester.ALL_HTTP_REQUEST[(url, method)] = time.time()

    @staticmethod
    def _prepare_url_before_http_request(url, method):
        THttpRequester.consider_request_policy(url, method)
        url = TUrlUtf8Encode.convert_url_to_idna(url)
        o = urlsplit_pro(url)
        path = urllib.parse.unquote(o.path)
        path = urllib.parse.quote(path)
        url = urllib.parse.urlunsplit((o.scheme, o.netloc, path, o.query, o.fragment))
        return url

    @staticmethod
    def get_content_type_from_headers(headers, default_value="text"):
        return headers.get('Content-Type', headers.get('Content-type', headers.get('content-type', default_value)))

    @staticmethod
    def get_file_extension_by_content_type(headers):
        content_disposition = headers.get('Content-Disposition', headers.get('content-disposition'))
        if content_disposition is not None:
            found = re.findall("filename\s*=\s*(.+)", content_disposition.lower())
            if len(found) > 0:
                filename = found[0].strip("\"")
                _, file_extension = os.path.splitext(filename)
                return file_extension
        content_type = THttpRequester.get_content_type_from_headers(headers)
        return content_type_to_file_extension(content_type)

    @staticmethod
    def make_http_request_urllib(url, method, timeout):
        assert THttpRequester.logger is not None
        assert method in {"GET", "HEAD"}

        if not url.lower().startswith('http'):
            raise THttpRequester.RobotHttpException('unknown protocol, can be only http or https', url, 520, method)

        try:
            url = THttpRequester._prepare_url_before_http_request(url, method)

            req = urllib.request.Request(
                url,
                data=None,
                headers={'User-Agent': get_user_agent()},
                method=method
            )

            with urllib.request.urlopen(req, context=THttpRequester.SSL_CONTEXT, timeout=timeout) as request:
                headers = request.info()
                data = ''
                if method == 'GET':
                    file_extension = THttpRequester.get_file_extension_by_content_type(headers)
                    if not is_video_or_audio_file_extension(file_extension) or THttpRequester.ENABLE_VIDEO_AND_AUDIO:
                        data = request.read()
                THttpRequester.register_successful_request()
                return request.geturl(), headers, data
        except IndexError as exp:
            raise THttpRequester.RobotHttpException("general IndexError inside urllib.request.urlopen",
                                                    url, 520, method)
        except UnicodeError as exp:
            raise THttpRequester.RobotHttpException("cannot redirect to cyrillic web domains or some unicode error",
                                                    url, 520, method)
        except (ConnectionError, http.client.HTTPException) as exp:
            raise THttpRequester.RobotHttpException(str(exp), url, 520, method)
        except socket.timeout as exp:
            THttpRequester.logger.error("socket timeout, while getting {}: {}".format(url, exp))
            raise THttpRequester.RobotHttpException("socket.timeout", url, 504, method)
        except ssl.SSLError as exp:
            THttpRequester.logger.error("ssl error, while getting {}: {}".format(url, exp))
            raise THttpRequester.RobotHttpException("ssl.SSLError", url, 504, method)
        except urllib.error.URLError as exp:
            code = -1
            if hasattr(exp, 'code'):
                code = exp.code

            raise THttpRequester.RobotHttpException("{} extype:{}".format(str(exp), type(exp)), url, code, method) #
        except urllib.error.HTTPError as e:
            if e.code == 503:
                THttpRequester.deal_with_http_code_503()
            if e.code == 405 and method == "HEAD":
                return THttpRequester.make_http_request_urllib(url, "GET", timeout)
            raise THttpRequester.RobotHttpException("{} extype:{}".format(str(e), type(e)), url, e.code, method)


    @staticmethod
    def make_http_request_urllib3(url, method, timeout):
        assert THttpRequester.logger is not None
        assert method in {"GET", "HEAD"}

        if not url.lower().startswith('http'):
            raise THttpRequester.RobotHttpException('unknown protocol, can be only http or https', url, 520, method)

        try:
            url = THttpRequester._prepare_url_before_http_request(url, method)
            http_pool = urllib3.PoolManager(
                #ca_certs=certifi.where()
            )
            THttpRequester.logger.debug("urllib.request.urlopen ({}) method={}".format(url, method))
            req = http_pool.request(method,
                         url,
                         headers={'User-Agent': get_user_agent()},
                         timeout=timeout
                         )
            if req.status >= 400:
                raise THttpRequester.RobotHttpException('get http code={}, while requesting {}, method={}',
                                                        req.status, url, method)
            headers = dict(req.headers)
            data = ''
            if method == 'GET':
                file_extension = THttpRequester.get_file_extension_by_content_type(headers)
                if not is_video_or_audio_file_extension(file_extension) or THttpRequester.ENABLE_VIDEO_AND_AUDIO:
                    data = req.data
            THttpRequester.register_successful_request()
            return get_redirected_url_urllib3(req, url), headers, data
        except IndexError as exp:
            raise THttpRequester.RobotHttpException("general IndexError inside urllib.request.urlopen",
                                                    url, 520, method)
        except (ConnectionError, http.client.HTTPException) as exp:
            raise THttpRequester.RobotHttpException(str(exp), url, 520, method)
        except socket.timeout as exp:
            THttpRequester.logger.error("socket timeout, while getting {}: {}".format(url, exp))
            raise THttpRequester.RobotHttpException("socket.timeout", url, 504, method)
        except ssl.SSLError as exp:
            THttpRequester.logger.error("ssl error, while getting {}: {}".format(url, exp))
            raise THttpRequester.RobotHttpException("ssl.SSLError", url, 504, method)
        except urllib3.exceptions.HTTPError as exp:
            code = -1
            if hasattr(exp, 'code'):
                code = exp.code
            if code == 503:
                THttpRequester.deal_with_http_code_503()
            if code == 405 and method == "HEAD":
                return THttpRequester.make_http_request_urllib(url, "GET", timeout)
            raise THttpRequester.RobotHttpException("{} extype:{}".format(str(exp), type(exp)), url, code, method) #

    @staticmethod
    def make_http_request_curl(url, method, timeout):
        if not url.lower().startswith('http'):
            raise THttpRequester.RobotHttpException('unknown protocol, can be http or https', url, 400, method)
        url = THttpRequester._prepare_url_before_http_request(url, method)
        curl = pycurl.Curl()
        try:
            curl.setopt(curl.URL, url)
        except UnicodeError as exp:
            raise THttpRequester.RobotHttpException("unicode error", url, 520, method)
        curl_response = TCurlResponse(url, method)
        curl.setopt(curl.HEADERFUNCTION, curl_response.collect_http_headers)
        if method == "HEAD":
            curl.setopt(curl.NOBODY, True)
        curl.setopt(curl.FOLLOWLOCATION, True)
        curl.setopt(pycurl.SSL_VERIFYPEER, False)
        assert timeout > 20
        curl.setopt(curl.CONNECTTIMEOUT, 20)
        curl.setopt(curl.TIMEOUT, timeout)

        curl.setopt(curl.CAINFO, certifi.where())
        curl.setopt(curl.SSL_CIPHER_LIST, DLROBOT_CIPHERS_LIST)
        user_agent = get_user_agent()
        curl.setopt(curl.USERAGENT, user_agent)
        curl.setopt(curl.WRITEFUNCTION, curl_response.write_callback)
        try:
            curl.perform()
            http_code = curl.getinfo(curl.RESPONSE_CODE)
            curl.close()

            if http_code < 200 or http_code >= 300:
                if http_code == 503:
                    THttpRequester.deal_with_http_code_503()
                if http_code == 405 and method == "HEAD":
                    return THttpRequester.make_http_request_curl(url, "GET", timeout)
                raise THttpRequester.RobotHttpException("curl failed", url, http_code, method)
            THttpRequester.register_successful_request()
            return curl_response.get_redirected_url(), curl_response.headers, curl_response.data
        except pycurl.error as err:
            THttpRequester.logger.debug("curl   exception {}".format(err))
            if err.args[0] == pycurl.E_WRITE_ERROR:
                # stop reading video content
                return curl_response.get_redirected_url(), curl_response.headers, curl_response.data

            raise THttpRequester.RobotHttpException(str(err), url, 520, method)
        except THttpRequester.RobotHttpException as exp:
            raise exp
        except Exception as exp:
            THttpRequester.logger.debug("unknown exception {}, curl url={}".format(exp, url))
            raise THttpRequester.RobotHttpException(str(exp), url, 520, method)

    @staticmethod
    def request_url_headers_with_global_cache(url):
        if url in THttpRequester.HEADER_MEMORY_CACHE:
            return THttpRequester.HEADER_MEMORY_CACHE[url]
        # do not ddos sites
        elapsed_time = datetime.datetime.now() - THttpRequester.LAST_HEAD_REQUEST_TIME
        if elapsed_time.total_seconds() < THttpRequester.SECONDS_BETWEEN_HEAD_REQUESTS:
            time.sleep(THttpRequester.SECONDS_BETWEEN_HEAD_REQUESTS - elapsed_time.total_seconds())
        THttpRequester.LAST_HEAD_REQUEST_TIME = datetime.datetime.now()

        redirected_url, headers, _ = THttpRequester.make_http_request(url, "HEAD")
        THttpRequester.HEADER_MEMORY_CACHE[url] = (redirected_url, headers)
        if redirected_url != url:
            THttpRequester.HEADER_MEMORY_CACHE[redirected_url] = (redirected_url,headers)
        return redirected_url, headers

    @staticmethod
    def check_urllib_access_with_many_head_requests(url):
        #see  https://minzdrav.gov.ru
        for i in range(3):
            start_time = time.time()
            try:
                THttpRequester.make_http_request(url, "HEAD")
            except THttpRequester.RobotHttpException as exp:
                pass

            if time.time() - start_time > 10:
                return False
            time.sleep(2)
        return True

    @staticmethod
    def make_http_request(url, method, timeout=None):
        if timeout is None:
            timeout = THttpRequester.DEFAULT_HTTP_TIMEOUT
        start_time = time.time()
        THttpRequester.logger.debug("make_http_request start ({}) method={}".format(url, method))
        try:
            if THttpRequester.HTTP_LIB == "urllib":
                return THttpRequester.make_http_request_urllib(url, method, timeout)
            elif THttpRequester.HTTP_LIB == "curl":
                return THttpRequester.make_http_request_curl(url, method, timeout)
            elif THttpRequester.HTTP_LIB == "urllib3":
                return THttpRequester.make_http_request_urllib3(url, method, timeout)
            else:
                raise Exception("unknown http_lib=\"{}\", can be urllib, curl or urllib3".format(THttpRequester.HTTP_LIB))
        except UnicodeError as exp:
            raise THttpRequester.RobotHttpException("cannot redirect to cyrillic web domains or some unicode error",
                                                    url, 520, method)
        finally:

            THttpRequester.logger.debug("make_http_request, elapsed time: {0:0.3f}".format(time.time() - start_time))


from common.content_types import content_type_to_file_extension, is_video_or_audio_file_extension
from common.primitives import TUrlUtf8Encode

import ssl

import urllib3
urllib3.disable_warnings()
urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'

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
from functools import partial
import os
import random


#for curl
import pycurl
from io import BytesIO
import certifi


def has_cyrillic(text):
    return bool(re.search('[Ёёа-яА-Я]', text))


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


def convert_russian_web_domain_if_needed(url):
    o = list(urllib.parse.urlparse(url)[:])
    if has_cyrillic(o[1]):
        o[1] = TUrlUtf8Encode.to_idna(o[1])

    o[2] = urllib.parse.unquote(o[2])
    o[2] = urllib.parse.quote(o[2])
    url = urllib.parse.urlunparse(o)
    return url


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


class THttpRequester:
    HTTP_TIMEOUT = 30  # in seconds
    ENABLE = True
    SECONDS_BETWEEN_HEAD_REQUESTS = 1.0
    REQUEST_RATE_1_MIN = 50
    REQUEST_RATE_10_MIN = 300
    ALL_HTTP_REQUEST = dict()  # (url, method) -> time
    HTTP_EXCEPTION_COUNTER = defaultdict(int)  # (url, method) -> number of exception
    HTTP_503_ERRORS_COUNT = 0
    SSL_CONTEXT = None
    HTTP_LIB = os.environ.get("DLROBOT_HTTP_LIB", "urllib")
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
        THttpRequester.SSL_CONTEXT.set_ciphers('DEFAULT@SECLEVEL=1')
        #THttpRequester.SSL_CONTEXT.set_ciphers('HIGH:!DH:!aNULL')
        if os.environ.get("DLROBOT_HTTP_TIMEOUT"):
            THttpRequester.logger.info("set http timeout to {}".format(os.environ.get("DLROBOT_HTTP_TIMEOUT")))
            THttpRequester.HTTP_TIMEOUT = int(os.environ.get("DLROBOT_HTTP_TIMEOUT"))

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
        return convert_russian_web_domain_if_needed(url)

    @staticmethod
    def get_content_type_from_headers(headers, default_value="text"):
        return headers.get('Content-Type', headers.get('Content-type', headers.get('content-type', default_value)))

    @staticmethod
    def get_file_extension_by_content_type(headers):
        content_disposition = headers.get('Content-Disposition')
        if content_disposition is not None:
            found = re.findall("filename\s*=\s*(.+)", content_disposition.lower())
            if len(found) > 0:
                filename = found[0].strip("\"")
                _, file_extension = os.path.splitext(filename)
                return file_extension
        content_type = THttpRequester.get_content_type_from_headers(headers)
        return content_type_to_file_extension(content_type)

    @staticmethod
    def make_http_request_urllib(url, method):
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

            THttpRequester.logger.debug("urllib.request.urlopen ({}) method={}".format(url, method))
            with urllib.request.urlopen(req, context=THttpRequester.SSL_CONTEXT, timeout=THttpRequester.HTTP_TIMEOUT) as request:
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
                return THttpRequester.make_http_request_urllib(url, "GET")
            raise THttpRequester.RobotHttpException("{} extype:{}".format(str(e), type(e)), url, e.code, method)


    @staticmethod
    def make_http_request_urllib3(url, method):
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
                         timeout=THttpRequester.HTTP_TIMEOUT
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
        except urllib3.exceptions.HTTPError as exp:
            code = -1
            if hasattr(exp, 'code'):
                code = exp.code
            if code == 503:
                THttpRequester.deal_with_http_code_503()
            if code == 405 and method == "HEAD":
                return THttpRequester.make_http_request_urllib(url, "GET")
            raise THttpRequester.RobotHttpException("{} extype:{}".format(str(exp), type(exp)), url, code, method) #

    @staticmethod
    def collect_http_headers_for_curl(header_dict, header_line):
        header_line = header_line.decode('iso-8859-1')

        # Ignore all lines without a colon
        if ':' not in header_line:
            return

        # Break the header line into header name and value
        h_name, h_value = header_line.split(':', 1)

        # Remove whitespace that may be present
        h_name = h_name.strip()
        h_value = h_value.strip()
        h_name = h_name.lower() # Convert header names to lowercase
        header_dict[h_name] = h_value # Header name and value.
        if h_name.lower() == "location" and h_value.startswith('http'):
            header_dict['last_full_redirected_url'] = h_value

    @staticmethod
    def make_http_request_curl(url, method):
        if not url.lower().startswith('http'):
            raise THttpRequester.RobotHttpException('unknown protocol, can be http or https', url, 400, method)
        url = THttpRequester._prepare_url_before_http_request(url, method)
        buffer = BytesIO()
        curl = pycurl.Curl()
        try:
            curl.setopt(curl.URL, url)
        except UnicodeError as exp:
            raise THttpRequester.RobotHttpException("unicode error", url, 520, method)
        headers = dict()
        curl.setopt(curl.HEADERFUNCTION, partial(THttpRequester.collect_http_headers_for_curl, headers))
        if method == "HEAD":
            curl.setopt(curl.NOBODY, True)
        else:
            curl.setopt(curl.WRITEDATA, buffer)
        curl.setopt(curl.FOLLOWLOCATION, True)
        curl.setopt(pycurl.SSL_VERIFYPEER, False)
        assert THttpRequester.HTTP_TIMEOUT > 20
        curl.setopt(curl.CONNECTTIMEOUT, 20)
        curl.setopt(curl.TIMEOUT, THttpRequester.HTTP_TIMEOUT)

        curl.setopt(curl.CAINFO, certifi.where())
        curl.setopt(curl.SSL_CIPHER_LIST, 'DEFAULT:!DH')
        user_agent = get_user_agent()
        curl.setopt(curl.USERAGENT, user_agent)
        THttpRequester.logger.debug("curl ({}) method={}".format(url, method))
        try:
            curl.perform()
            http_code = curl.getinfo(curl.RESPONSE_CODE)
            THttpRequester.logger.debug('http_code = {} Time: {}'.format(http_code, curl.getinfo(curl.TOTAL_TIME)))
            curl.close()

            if http_code < 200 or http_code >= 300:
                if http_code == 503:
                    THttpRequester.deal_with_http_code_503()
                if http_code == 405 and method == "HEAD":
                    return THttpRequester.make_http_request_curl(url, "GET")
                raise THttpRequester.RobotHttpException("curl failed", url, http_code, method)
            data = b"" if method == "HEAD" else buffer.getvalue()
            redirected_url = headers.get('last_full_redirected_url', url)
            THttpRequester.register_successful_request()
            return redirected_url, headers, data
        except pycurl.error as err:
            raise THttpRequester.RobotHttpException(str(err), url, 520, method)

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
    def make_http_request(url, method):
        if THttpRequester.HTTP_LIB == "urllib":
            return THttpRequester.make_http_request_urllib(url, method)
        elif THttpRequester.HTTP_LIB == "curl":
            return THttpRequester.make_http_request_curl(url, method)
        elif THttpRequester.HTTP_LIB == "urllib3":
            return THttpRequester.make_http_request_urllib3(url, method)
        else:
            raise Exception("unknown http_lib, can be urllib, curl or urllib3")



import ssl
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
#for curl
import pycurl
from io import BytesIO
import certifi


class TRequestPolicy:
    HTTP_TIMEOUT = 30  # in seconds
    ENABLE = True
    SECONDS_BETWEEN_HEAD_REQUESTS = 1.0
    REQUEST_RATE_1_MIN = 50
    REQUEST_RATE_10_MIN = 300
    ALL_HTTP_REQUEST = dict()  # (url, method) -> time
    HTTP_EXCEPTION_COUNTER = defaultdict(int)  # (url, method) -> number of exception
    HTTP_503_ERRORS_COUNT = 0
    SSL_CONTEXT = None
    USE_CURL = False

    @staticmethod
    def initialize():
        TRequestPolicy.SSL_CONTEXT = ssl._create_unverified_context()
        TRequestPolicy.SSL_CONTEXT.set_ciphers('HIGH:!DH:!aNULL')

    # decrement HTTP_503_ERRORS_COUNT on successful http_request
    @staticmethod
    def register_successful_request():
        if TRequestPolicy.ENABLE:
            if TRequestPolicy.HTTP_503_ERRORS_COUNT > 0:
                TRequestPolicy.HTTP_503_ERRORS_COUNT -= 1  # decrement HTTP_503_ERRORS_COUNT on successful http_request

    @staticmethod
    def get_request_rate(min_time=0):
        current_time = time.time()
        time_points = list(t for t in TRequestPolicy.ALL_HTTP_REQUEST.values() if t > min_time)
        return {
            "request_rate_1_min": sum(1 for t in time_points if (current_time - t) < 60),
            "request_rate_10_min": sum(1 for t in time_points if (current_time - t) < 60 * 10),
            "request_count": len(time_points)
        }

    @staticmethod
    def deal_with_http_code_503(logger):
        if not TRequestPolicy.ENABLE:
            return
        request_rates = TRequestPolicy.get_request_rate()
        logger.error("got HTTP-503 got, request_rate={}".format(json.dumps(request_rates)))
        max_http_503_errors_count = 20
        TRequestPolicy.HTTP_503_ERRORS_COUNT += 1
        if TRequestPolicy.HTTP_503_ERRORS_COUNT > max_http_503_errors_count:
            logger.error("full stop after {} HTTP-503 errors to prevent a possible ddos attack".format(
                max_http_503_errors_count))
            sys.exit(1)
        else:
            logger.error("wait 1 minute after HTTP-503 N {}".format(TRequestPolicy.HTTP_503_ERRORS_COUNT))
            time.sleep(60)
            if TRequestPolicy.HTTP_503_ERRORS_COUNT + 1 > max_http_503_errors_count:
                logger.error("last chance before exit, wait 20 minutes")
                time.sleep(20 * 60)

    @staticmethod
    def wait_until_policy_compliance(logger, policy_name, max_policy_value):
        if not TRequestPolicy.ENABLE:
            return
        request_rates = TRequestPolicy.get_request_rate()
        sleep_sec = max_policy_value / 10
        while request_rates[policy_name] > max_policy_value:
            logger.debug("wait {} seconds to comply {} (max value={})".format(sleep_sec, policy_name, max_policy_value))
            time.sleep(sleep_sec)
            request_rates = TRequestPolicy.get_request_rate()

    @staticmethod
    def consider_request_policy(logger, url, method):
        if not TRequestPolicy.ENABLE:
            return

        if TRequestPolicy.HTTP_EXCEPTION_COUNTER[(url, method)] > 2:
            raise RobotHttpException("stop requesting the same url", url, 429, method)

        if len(TRequestPolicy.ALL_HTTP_REQUEST) > 80:
            TRequestPolicy.wait_until_policy_compliance(logger, "request_rate_1_min", TRequestPolicy.REQUEST_RATE_1_MIN)
            TRequestPolicy.wait_until_policy_compliance(logger, "request_rate_10_min", TRequestPolicy.REQUEST_RATE_10_MIN)

        TRequestPolicy.ALL_HTTP_REQUEST[(url, method)] = time.time()

TRequestPolicy.initialize()


def has_cyrillic(text):
    return bool(re.search('[Ёёа-яА-Я]', text))


class RobotHttpException(Exception):
    def __init__(self, value, url, http_code, http_method):
        key = (url, http_method)
        if TRequestPolicy.ENABLE:
            TRequestPolicy.HTTP_EXCEPTION_COUNTER[key] = TRequestPolicy.HTTP_EXCEPTION_COUNTER[key] + 1
            self.count = TRequestPolicy.HTTP_EXCEPTION_COUNTER[key]
        else:
            self.count = 1
        self.value = value
        self.url = url
        self.http_code = http_code
        self.http_method = http_method

    def __str__(self):
        return "cannot make http-request ({}) to {} got code {}, initial exception: {}".format( \
            self.http_method, self.url, self.http_code, self.value)


def convert_russian_web_domain_if_needed(url):
    o = list(urllib.parse.urlparse(url)[:])
    if has_cyrillic(o[1]):
        o[1] = o[1].encode('idna').decode('latin')

    o[2] = urllib.parse.unquote(o[2])
    o[2] = urllib.parse.quote(o[2])
    url = urllib.parse.urlunparse(o)
    return url


def _prepare_url_before_http_request(logger, url, method):
    if url.find('://') == -1:
        url = "http://" + url

    TRequestPolicy.consider_request_policy(logger, url, method)

    return convert_russian_web_domain_if_needed(url)


def get_user_agent():
    return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'


if os.environ.get("DLROBOT_HTTP_TIMEOUT"):
    #print ("set http timeout to {}".format(os.environ.get("DLROBOT_HTTP_TIMEOUT")))
    TRequestPolicy.HTTP_TIMEOUT = int(os.environ.get("DLROBOT_HTTP_TIMEOUT"))


def make_http_request_urllib(logger, url, method):
    url = _prepare_url_before_http_request(logger, url, method)

    req = urllib.request.Request(
        url,
        data=None,
        headers={'User-Agent': get_user_agent()},
        method=method
    )

    logger.debug("urllib.request.urlopen ({}) method={}".format(url, method))
    try:
        with urllib.request.urlopen(req, context=TRequestPolicy.SSL_CONTEXT, timeout=TRequestPolicy.HTTP_TIMEOUT) as request:
            data = '' if method == "HEAD" else request.read()
            headers = request.info()
            TRequestPolicy.register_successful_request()
            return request.geturl(), headers, data
    except UnicodeError as exp:
        raise RobotHttpException("cannot redirect to cyrillic web domains or some unicode error", url, 520, method)
    except (ConnectionError, http.client.HTTPException) as exp:
        raise RobotHttpException(str(exp), url, 520, method)
    except socket.timeout as exp:
        logger.error("socket timeout, while getting {}: {}".format(url, exp))
        raise RobotHttpException("socket.timeout", url, 504, method)
    except urllib.error.URLError as exp:
        code = -1
        if hasattr(exp, 'code'):
            code = exp.code

        raise RobotHttpException("{} extype:{}".format(str(exp), type(exp)), url, code, method) #
    except urllib.error.HTTPError as e:
        if e.code == 503:
            TRequestPolicy.deal_with_http_code_503(logger)
        if e.code == 405 and method == "HEAD":
            return make_http_request_urllib(logger, url, "GET")
        raise RobotHttpException("{} extype:{}".format(str(e), type(e)), url, e.code, method)



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


def make_http_request_curl(logger, url, method):
    url = _prepare_url_before_http_request(logger, url, method)
    buffer = BytesIO()
    curl = pycurl.Curl()
    try:
        curl.setopt(curl.URL, url)
    except UnicodeError as exp:
        raise RobotHttpException("unicode error", url, 520, method)
    headers = dict()
    curl.setopt(curl.HEADERFUNCTION, partial(collect_http_headers_for_curl, headers))
    if method == "HEAD":
        curl.setopt(curl.NOBODY, True)
    else:
        curl.setopt(curl.WRITEDATA, buffer)
    curl.setopt(curl.FOLLOWLOCATION, True)
    assert TRequestPolicy.HTTP_TIMEOUT > 20
    curl.setopt(curl.CONNECTTIMEOUT, 20)
    curl.setopt(curl.TIMEOUT, TRequestPolicy.HTTP_TIMEOUT)

    curl.setopt(curl.CAINFO, certifi.where())
    user_agent = get_user_agent()
    curl.setopt(curl.USERAGENT, user_agent)
    logger.debug("curl ({}) method={}".format(url, method))
    try:
        curl.perform()
        http_code = curl.getinfo(curl.RESPONSE_CODE)
        logger.debug('http_code = {} Time: {}'.format(http_code, curl.getinfo(curl.TOTAL_TIME)))
        curl.close()

        if http_code < 200 or http_code >= 300:
            if http_code == 503:
                TRequestPolicy.deal_with_http_code_503(logger)
            if http_code == 405 and method == "HEAD":
                return make_http_request_curl(logger, url, "GET")
            raise RobotHttpException("curl failed", url, http_code, method)
        data = b"" if method == "HEAD" else buffer.getvalue()
        redirected_url = headers.get('Location', headers.get('location', url))
        TRequestPolicy.register_successful_request()
        return redirected_url, headers, data
    except pycurl.error as err:
        raise RobotHttpException(str(err), url, 520, method)


LAST_HEAD_REQUEST_TIME = datetime.datetime.now()
HEADER_MEMORY_CACHE = dict()


def request_url_headers_with_global_cache(logger, url):
    global HEADER_MEMORY_CACHE,  LAST_HEAD_REQUEST_TIME
    if url in HEADER_MEMORY_CACHE:
        return HEADER_MEMORY_CACHE[url]
    # do not ddos sites
    elapsed_time = datetime.datetime.now() - LAST_HEAD_REQUEST_TIME
    if elapsed_time.total_seconds() < TRequestPolicy.SECONDS_BETWEEN_HEAD_REQUESTS:
        time.sleep(TRequestPolicy.SECONDS_BETWEEN_HEAD_REQUESTS - elapsed_time.total_seconds())
    LAST_HEAD_REQUEST_TIME = datetime.datetime.now()

    redirected_url, headers, _ = make_http_request(logger, url, "HEAD")
    HEADER_MEMORY_CACHE[url] = (redirected_url, headers)
    if redirected_url != url:
        HEADER_MEMORY_CACHE[redirected_url] = (redirected_url,headers)
    return redirected_url, headers


def make_http_request(logger, url, method):
    if TRequestPolicy.USE_CURL:
        return make_http_request_curl(logger, url, method)
    else:
        return make_http_request_urllib(logger, url, method)




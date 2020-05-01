import ssl
import logging
import urllib.error
import urllib.request
import urllib.parse
from collections import defaultdict
import time
import datetime
import re
import sys
import json

ALL_HTTP_REQUEST = dict() # (url, method) -> time
LAST_HEAD_REQUEST_TIME = datetime.datetime.now()
HEADER_MEMORY_CACHE = dict()
HEADER_REQUEST_COUNT = defaultdict(int)
HTTP_503_ERRORS_COUNT = 0


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


def has_cyrillic(text):
    return bool(re.search('[Ёёа-яА-Я]', text))


def make_http_request(url, method):
    global HTTP_503_ERRORS_COUNT
    consider_request_policy(url, method)

    if url.find('://') == -1:
        url = "http://" + url

    o = list(urllib.parse.urlparse(url)[:])
    if has_cyrillic(o[1]):
        o[1] = o[1].encode('idna').decode('latin')

    o[2] = urllib.parse.unquote(o[2])
    o[2] = urllib.parse.quote(o[2])
    url = urllib.parse.urlunparse(o)
    context = ssl._create_unverified_context()
    redirect_handler = urllib.request.HTTPRedirectHandler()
    redirect_handler.max_redirections = 5
    opener = urllib.request.build_opener(redirect_handler)
    urllib.request.install_opener(opener)

    req = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        },
        method=method
    )

    logger = logging.getLogger("dlrobot_logger")
    logger.debug("urllib.request.urlopen ({}) method={}".format(url, method))
    try:
        with urllib.request.urlopen(req, context=context, timeout=20.0) as request:
            data = '' if method == "HEAD" else request.read()
            headers = request.info()
            if HTTP_503_ERRORS_COUNT > 0:
                HTTP_503_ERRORS_COUNT -= 1 #decrement HTTP_503_ERRORS_COUNT on successful http_request
            return request.geturl(), headers, data
    except urllib.error.HTTPError as e:
        if e.code == 503:
            request_rates = get_request_rate()
            logger.error("got HTTP-503 got, request_rate={}".format(json.dumps(request_rates)))
            max_http_503_errors_count = 20
            HTTP_503_ERRORS_COUNT += 1
            if HTTP_503_ERRORS_COUNT > max_http_503_errors_count:
                logger.error("full stop after {} HTTP-503 errors to prevent a possible ddos attack".format(max_http_503_errors_count))
                #see http://bruhoveckaya.ru
                sys.exit(1)
            else:
                logger.error("wait 1 minute after HTTP-503 N {}".format(HTTP_503_ERRORS_COUNT))
                time.sleep(60)
                if HTTP_503_ERRORS_COUNT + 1 > max_http_503_errors_count:
                    time.sleep(20*60)  # last chance, wait 20 minutes

        raise


class HttpHeadException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


def request_url_headers(url):
    global HEADER_MEMORY_CACHE, HEADER_REQUEST_COUNT, LAST_HEAD_REQUEST_TIME
    if url in HEADER_MEMORY_CACHE:
        return HEADER_MEMORY_CACHE[url]
    if HEADER_REQUEST_COUNT[url] >= 3:
        raise HttpHeadException("too many times to get headers that caused exceptions")

    # do not ddos sites
    elapsed_time = datetime.datetime.now() - LAST_HEAD_REQUEST_TIME
    if elapsed_time.total_seconds() < 1:
        time.sleep(1)
    LAST_HEAD_REQUEST_TIME = datetime.datetime.now()


    HEADER_REQUEST_COUNT[url] += 1
    redirected_url, headers, _ = make_http_request(url, "HEAD")
    HEADER_MEMORY_CACHE[url] = (redirected_url, headers)
    if redirected_url != url:
        HEADER_MEMORY_CACHE[redirected_url] = (redirected_url,headers)
    return redirected_url, headers

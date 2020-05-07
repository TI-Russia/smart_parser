import logging
import pycurl
from collections import defaultdict
import time
import datetime
import sys
import json
from io import BytesIO
import certifi

ALL_HTTP_REQUEST = dict()  # (url, method) -> time
HTTP_EXCEPTION_COUNTER = defaultdict(int)  # (url, method) -> number of exception
LAST_HEAD_REQUEST_TIME = datetime.datetime.now()
HEADER_MEMORY_CACHE = dict()
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


class RobotHttpException(Exception):
    def __init__(self, value, url, http_code, http_method):
        global HTTP_EXCEPTION_COUNTER
        key = (url, http_method)
        HTTP_EXCEPTION_COUNTER[key] = HTTP_EXCEPTION_COUNTER[key] + 1
        self.count = HTTP_EXCEPTION_COUNTER[key]
        self.value = value
        self.url = url
        self.http_code = http_code
        self.http_method = http_method

    def __str__(self):
        return "cannot make http-request ({}) to {} got code {}, initial exception: {}".format( \
            self.http_method, self.url, self.http_code, self.value)

LAST_HTTP_HEADERS = None
def display_header(header_line):
    global LAST_HTTP_HEADERS
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
    LAST_HTTP_HEADERS[h_name] = h_value # Header name and value.


def deal_with_http_code_503():
    global HTTP_503_ERRORS_COUNT
    logger = logging.getLogger("dlrobot_logger")
    request_rates = get_request_rate()
    logger.error("got HTTP-503 got, request_rate={}".format(json.dumps(request_rates)))
    max_http_503_errors_count = 20
    HTTP_503_ERRORS_COUNT += 1
    if HTTP_503_ERRORS_COUNT > max_http_503_errors_count:
        logger.error("full stop after {} HTTP-503 errors to prevent a possible ddos attack".format(
            max_http_503_errors_count))
        sys.exit(1)
    else:
        logger.error("wait 1 minute after HTTP-503 N {}".format(HTTP_503_ERRORS_COUNT))
        time.sleep(60)
        if HTTP_503_ERRORS_COUNT + 1 > max_http_503_errors_count:
            time.sleep(20 * 60)  # last chance, wait 20 minutes


def make_http_request(url, method):
    global HTTP_503_ERRORS_COUNT
    global HTTP_EXCEPTION_COUNTER
    global LAST_HTTP_HEADERS
    if HTTP_EXCEPTION_COUNTER[(url, method)] > 2:
        raise RobotHttpException("stop requesting the same url", url, 429, method)

    consider_request_policy(url, method)

    buffer = BytesIO()
    curl = pycurl.Curl()
    curl.setopt(curl.URL, url)
    curl.setopt(curl.HEADERFUNCTION, display_header)
    if method == "HEAD":
        curl.setopt(curl.NOBODY, True)
    else:
        curl.setopt(curl.WRITEDATA, buffer)
    curl.setopt(curl.FOLLOWLOCATION, True)
    curl.setopt(curl.CONNECTTIMEOUT, 20)
    curl.setopt(curl.TIMEOUT, 60)
    curl.setopt(curl.CAINFO, certifi.where())
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    curl.setopt(curl.USERAGENT, user_agent)
    logger = logging.getLogger("dlrobot_logger")
    logger.debug("urllib.request.urlopen ({}) method={}".format(url, method))
    try:
        LAST_HTTP_HEADERS = dict()
        curl.perform()
        http_code = curl.getinfo(curl.RESPONSE_CODE)
        print('http_code = {} Time: {}'.format(http_code, curl.getinfo(curl.TOTAL_TIME)))
        curl.close()

        if http_code < 200 or http_code >= 300:
            if http_code == 503:
                deal_with_http_code_503()
            raise RobotHttpException("curl failed", url, http_code, method)
        data = b"" if method == "HEAD" else buffer.getvalue()
        headers = dict(LAST_HTTP_HEADERS)
        redirected_url = headers.get('Location', headers.get('location', url))
        if HTTP_503_ERRORS_COUNT > 0:
            HTTP_503_ERRORS_COUNT -= 1  # decrement HTTP_503_ERRORS_COUNT on successful http_request
        return redirected_url, headers, data
    except pycurl.error as err:
        raise RobotHttpException(str(err), url, 520, method)


def request_url_headers(url):
    global HEADER_MEMORY_CACHE,  LAST_HEAD_REQUEST_TIME
    if url in HEADER_MEMORY_CACHE:
        return HEADER_MEMORY_CACHE[url]
    # do not ddos sites
    elapsed_time = datetime.datetime.now() - LAST_HEAD_REQUEST_TIME
    if elapsed_time.total_seconds() < 1:
        time.sleep(1)
    LAST_HEAD_REQUEST_TIME = datetime.datetime.now()

    redirected_url, headers, _ = make_http_request(url, "HEAD")
    HEADER_MEMORY_CACHE[url] = (redirected_url, headers)
    if redirected_url != url:
        HEADER_MEMORY_CACHE[redirected_url] = (redirected_url,headers)
    return redirected_url, headers

if __name__ == "__main__":
    #redirected_url, headers, data = make_http_request("www.yandex.ru", "GET")
    #redirected_url, headers, data = make_http_request("www.yandex.ru", "HEAD")
    #redirected_url, headers, data = make_http_request("http://www.aot.ru/docs/Nozhov/msot.pdf", "HEAD")
    #print (headers)

    #redirected_url, headers, data = make_http_request("http://www.aot.ru/docs/Nozhov/msot.pdf", "GET")
    #print (headers)
    #print (len(data))

    redirected_url, headers, data = make_http_request("http://www.aot.ru/docs/Nozhov/msot1.pdf", "GET")
    print (headers)

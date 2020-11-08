from robots.common.http_request import request_url_headers_with_global_cache, make_http_request, RobotHttpException
import logging


if __name__ == "__main__":
    redirected_url, headers = request_url_headers_with_global_cache(logging, "www.yandex.ru")
    assert headers is not None
    assert redirected_url == 'https://yandex.ru/'

    try:
        s = make_http_request(logging, "http://gibdd.ru", "GET")
    except RobotHttpException as exp:
        assert exp.http_code == 520
        #todo: why urlib cannot resolve redirects for http://gibdd.ru  -> гибдд.рф?

    try:
        s = make_http_request(logging, "http://5%20июня%20запретят%20розничную%20продажу%20алкоголя", "GET")
    except RobotHttpException as exp:
        #no UnicodeException for this url
        pass


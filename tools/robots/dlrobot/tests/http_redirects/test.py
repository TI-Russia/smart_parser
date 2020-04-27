from robots.common.http_request import request_url_headers

if __name__ == "__main__":
    redirected_url, headers = request_url_headers("www.yandex.ru")
    assert headers is not None
    assert redirected_url == 'https://yandex.ru/'
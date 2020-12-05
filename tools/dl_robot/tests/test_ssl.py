from common.http_request import make_http_request
import logging
from common.http_request import TRequestPolicy
from common.download import TDownloadEnv


if __name__ == "__main__":
    #test for TRequestPolicy.SSL_CONTEXT.set_ciphers('DEFAULT@SECLEVEL=1') in http_request.py

    TDownloadEnv.clear_cache_folder()
    TRequestPolicy.ENABLE = False

    make_http_request(logging, "www.yandex.ru", "GET")
    make_http_request(logging, "chukotka.sledcom.ru/", "GET")
    make_http_request(logging, "www.aot.ru", "GET")
    make_http_request(logging, "www.mid.ru", "GET")
    make_http_request(logging, "officefinder.rs", "GET")
    make_http_request(logging, "ozerny.ru", "GET")
    make_http_request(logging, "ksl.spb.sudrf.ru", "GET")
    make_http_request(logging, "spbogdo.ru", "GET")
    make_http_request(logging, "arshush.ru", "GET")
    make_http_request(logging, "akrvo.ru", "GET")
    make_http_request(logging, "http://primorie.fas.gov.ru", "GET")




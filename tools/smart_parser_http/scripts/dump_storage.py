import zlib

from smart_parser_http.smart_parser_server import TSmartParserHTTPServer
import sys
import dbm.gnu


if __name__ == "__main__":
    dbm = dbm.gnu.open(sys.argv[1], "r")
    k = dbm.firstkey()
    while k is not None:
        value = dbm.get(k)
        print("key")
        print("{}".format(k.decode('latin')))
        print("value")
        if value == TSmartParserHTTPServer.SMART_PARSE_FAIL_CONSTANT:
            print(value.decode('latin'))
        else:
            print(zlib.decompress(value).decode('utf8'))
        k = dbm.nextkey(k)

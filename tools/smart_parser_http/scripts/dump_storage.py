import zlib

from smart_parser_http.smart_parser_server import TSmartParserHTTPServer
import sys
import dbm.gnu


if __name__ == "__main__":
    dbm = dbm.gnu.open(sys.argv[1], "r")
    k = dbm.firstkey()
    while k is not None:
        value = dbm.get(k)
        if value == TSmartParserHTTPServer.SMART_PARSE_FAIL_CONSTANT:
            value = value.decode('latin')
        else:
            value = zlib.decompress(value).decode('utf8').replace('\n', ' ')
        print("{}\t{}".format(k.decode('latin'), value))
        k = dbm.nextkey(k)

from smart_parser_http.smart_parser_server import TSmartParserHTTPServer


import dbm.gnu
import zlib
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-keys", dest='only_keys', action="store_true", default=False)
    parser.add_argument("--smart-parser-format", dest='smart_parser_format', default=False, required=False,
                        action="store_true")
    parser.add_argument('files', nargs='*')
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = parse_args()
    for filename in args.files:
        dbm = dbm.gnu.open(filename, "r")
        k = dbm.firstkey()
        while k is not None:
            value = dbm.get(k)
            if args.only_keys:
                print(k.decode('latin'))
            else:
                if args.smart_parser_format:
                    if value == TSmartParserHTTPServer.SMART_PARSE_FAIL_CONSTANT:
                        value = value.decode('latin')
                    else:
                        value = zlib.decompress(value).decode('utf8').replace('\n', ' ')
                else:
                    value = value.decode('latin')
                print("{}\t{}".format(k.decode('latin'), value))
            k = dbm.nextkey(k)

from smart_parser_http.smart_parser_server import TSmartParserHTTPServer

import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', dest="db_file")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    TSmartParserHTTPServer.TASK_TIMEOUT = 1
    input_server = TSmartParserHTTPServer(TSmartParserHTTPServer.parse_args(['--cache-file', args.db_file]))
    input_server.delete_old_keys()
    input_server.stop_server(run_shutdown=False)

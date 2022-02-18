from common.logging_wrapper import setup_logging
import argparse
import sys
import http.client
import time
import json


def parse_args(arg_list):
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", dest='host')
    parser.add_argument("--use-http", dest='use_http', action="store_true", default=False)
    parser.add_argument("--input-requests", dest='input_requests')
    parser.add_argument("--user-agent", dest='user_agent', required=False, default="Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)")
    return parser.parse_args(arg_list)


def read_requests(input_requests_path):
    with open(input_requests_path) as inp:
        for l in inp:
            yield l.strip()


if __name__ == "__main__":
    logger = setup_logging(log_file_name="dolbilo.log")
    args = parse_args(sys.argv[1:])
    start_time = time.time()
    request_count = 0
    normal_response_count = 0
    for request in read_requests(args.input_requests):
        if args.use_http:
            conn = http.client.HTTPConnection(args.host)
        else:
            conn = http.client.HTTPSConnection(args.host)
        headers = {
            'User-Agent': args.user_agent
        }
        req_start = time.time()
        conn.request("GET", request, headers=headers)
        res = conn.getresponse()
        data = b""
        if res.status == 301:
            data = res.read()
            conn.request("GET", res.headers['Location'], headers=headers)
            res = conn.getresponse()
        if res.status == 301:
            data = res.read()
            conn.request("GET", res.headers['Location'], headers=headers)
            res = conn.getresponse()
        if res.status == 200:
            data = res.read()
        else:
            raise Exception("cannot fetch url={}".format(request))
        req_end = time.time()
        req_time = int(1000.0*(req_end - req_start))
        logger.debug("{}\t{}\t{}\t{}".format(request, res.status, len(data), req_time))
        request_count += 1

    end_time = time.time()
    rps = round(float(request_count) / (end_time - start_time), 2)
    metrics = {
        'rps': rps,
        'request_count': request_count
    }
    logger.info(json.dumps(metrics))

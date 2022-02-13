from common.logging_wrapper import setup_logging
from common.access_log import get_human_requests
import argparse
import sys
import http.client
import time
import json


def parse_args(arg_list):
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", dest='host')
    parser.add_argument("--use-http", dest='use_http', action="store_true", default=False)
    parser.add_argument("--input-access-log", dest='input_access_log')
    parser.add_argument("--expected-normal-count", dest='expected_normal_count', type=int)
    parser.add_argument("--user-agent", dest='user_agent', required=False, default="Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)")
    return parser.parse_args(arg_list)


if __name__ == "__main__":
    logger = setup_logging(log_file_name="dolbilo.log")
    args = parse_args(sys.argv[1:])
    requests = get_human_requests(args.input_access_log)
    start_time = time.time()
    request_count = 0
    normal_response_count = 0
    for request in requests:
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
            normal_response_count += 1
        req_end = time.time()
        req_time = int(1000.0*(req_end - req_start))
        logger.debug("{}\t{}\t{}\t{}".format(request, res.status, len(data), req_time))
        sys.stdout.flush()
        request_count += 1

    end_time = time.time()
    rps = round(float(request_count) / (end_time - start_time), 2)
    metrics = {
        'normal_response_count': normal_response_count,
        'rps': rps,
        'request_count': request_count
    }
    logger.debug(json.dumps(metrics))
    print(json.dumps(metrics))
    if args.expected_normal_count is not None:
        if args.expected_normal_count != normal_response_count:
            logger.error("expected_normal_count = {}, read_count={}".format(args.expected_normal_count, normal_response_count))
            sys.exit(1)

from common.logging_wrapper import setup_logging
import argparse
import sys
import re
import http.client
import gzip
import time
import json


def parse_args(arg_list):
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", dest='host')
    parser.add_argument("--use-http", dest='use_http', action="store_true", default=False)
    parser.add_argument("--input-access-log", dest='input_access_log')
    parser.add_argument("--user-agent", dest='user_agent', required=False, default="Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)")
    return parser.parse_args(arg_list)


def access_log_parser(line):
    # Regex for the common Apache log format.
    parts = [
        r'(?P<host>\S+)',  # host %h
        r'\S+',  # indent %l (unused)
        r'(?P<user>\S+)',  # user %u
        r'\[(?P<time>.+)\]',  # time %t
        r'"(?P<request>.*)"',  # request "%r"
        r'(?P<status>[0-9]+)',  # status %>s
        r'(?P<size>\S+)',  # size %b (careful, can be '-')
        r'"(?P<referrer>.*)"',  # referrer "%{Referer}i"
        r'"(?P<agent>.*)"',  # user agent "%{User-agent}i"
    ]
    pattern = re.compile(r'\s+'.join(parts) + r'\s*\Z')
    #print (line)
    return pattern.match(line).groupdict()


def is_bot_request(request):
    agent = request['agent']
    bots = ["YandexBot", "MJ12bot", "AhrefsBot", "Googlebot", "bingbot", "Baiduspider", "thonkphp", 'Python-urllib']
    for b in bots:
        if b in agent:
            return True
    return False


def read_requests(input_access_log_path):
    requests = list()

    with gzip.open(input_access_log_path) as inp:
        for line in inp:
            request = access_log_parser(line.decode("utf8"))
            if is_bot_request(request):
                continue
            if request['request'].startswith("GET "):
                path = request['request'].split()[1]
                if path.startswith('/static/dlrobot/'):
                    continue
                requests.append(path)
        return requests


if __name__ == "__main__":
    logger = setup_logging(log_file_name="dolbilo.log")
    args = parse_args(sys.argv[1:])
    requests = read_requests(args.input_access_log)
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
    rps = round((float)(request_count) / (end_time - start_time), 2)
    metrics = {
        'normal_response_count': normal_response_count,
        'rps': rps,
        'request_count': request_count
    }
    logger.debug(json.dumps(metrics))
    print(json.dumps(metrics))

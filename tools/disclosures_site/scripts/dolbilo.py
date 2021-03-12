import argparse
import sys
import re
import http.client
import gzip


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


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    requests = list()

    with gzip.open(args.input_access_log) as inp:
        for line in inp:
            request = access_log_parser(line.decode("utf8"))
            if not is_bot_request(request):
                if request['request'].startswith("GET "):
                    requests.append(request['request'].split()[1])

    for request in requests:
        if args.use_http:
            conn = http.client.HTTPConnection(args.host)
        else:
            conn = http.client.HTTPSConnection(args.host)
        headers = {
            'User-Agent': args.user_agent
        }
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
        #if res.status == 301
        print("{}\t{}\t{}\n".format(request, res.status, len(data)))

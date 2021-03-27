import re
import gzip


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
    parser = pattern.match(line)
    if parser is None:
        raise Exception("cannot parse line {}".format(line))
    return parser.groupdict()


def is_bot_request(request):
    agent = request['agent']
    bots = ["YandexBot", "MJ12bot", "AhrefsBot", "Googlebot", "bingbot", "Baiduspider",
            "thonkphp", 'Python-urllib', 'PetalBot', 'Adsbot']
    for b in bots:
        if b in agent:
            return True
    return False


def get_human_requests(input_access_log_path):
    requests = list()

    with gzip.open(input_access_log_path) as inp:
        for line in inp:
            try:
                request = access_log_parser(line.decode("utf8"))
            except Exception as exp:
                continue
            if is_bot_request(request):
                continue
            if request['request'].startswith("GET "):
                path = request['request'].split()[1]
                if path.startswith('/static/dlrobot/'):
                    continue
                requests.append(path)
        return requests

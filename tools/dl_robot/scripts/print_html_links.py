from common.primitives import get_site_domain_wo_www
import argparse
from bs4 import BeautifulSoup
from common.http_request import THttpRequester
from common.logging_wrapper import setup_logging

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--convert-to-domains",  dest='convert_to_domains', required=False, default=False, action="store_true")
    parser.add_argument("--input-html",  dest='input_html', required=False)
    parser.add_argument("--input-url", dest='input_url', required=False)
    args = parser.parse_args()
    return args


def print_links(file_path, convert_to_domains):
    with open(file_path, "rb") as inp:
        html_data = inp.read()
        soup = BeautifulSoup(html_data, 'html.parser')
        links_to_process = list(soup.findAll('a'))
        index = 0
        for l in links_to_process:
            href = l.attrs.get('href')
            if href is not None:
                if convert_to_domains:
                    href = get_site_domain_wo_www(href)
                print("{}: {} {}".format(index, href, l.get_text() ))
            index += 1

if __name__ == "__main__":
    args = parse_args()
    if args.input_html:
        print_links(args.input_html, args.convert_to_domains)
    else:
        url = args.input_url
        logger = setup_logging()
        THttpRequester.initialize(logger)
        _, _, file_data = THttpRequester.make_http_request(url, "GET")
        tmp_path = "/tmp/tmp.html"
        with open(tmp_path, "wb") as outp:
            outp.write(file_data)
        print_links(tmp_path, args.convert_to_domains)

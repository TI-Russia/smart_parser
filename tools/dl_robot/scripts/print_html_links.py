from common.primitives import get_site_domain_wo_www
import argparse
from bs4 import BeautifulSoup


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--convert-to-domains",  dest='convert_to_domains', required=False, default=False, action="store_true")
    parser.add_argument("--input",  dest='input', required=True)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    with open (args.input, "rb") as inp:
        html_data = inp.read()
        soup = BeautifulSoup(html_data, 'html.parser')
        links_to_process = list(soup.findAll('a'))
        for l in links_to_process:
            href = l.attrs.get('href')
            if href is not None:
                #href = href.decode('utf8')
                if args.convert_to_domains:
                    href = get_site_domain_wo_www(href)
                print(href)

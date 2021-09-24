from common.http_request import THttpRequester
from common.logging_wrapper import setup_logging
from common.download import TDownloadedFile
from common.html_parser import THtmlParser
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-cache",  dest="use_cache",action="store_true", default=False, required=False)
    parser.add_argument("--action", dest='action', default="links", help="can be: links, plain_text, utf8_html")
    parser.add_argument("urls", nargs="*")
    args = parser.parse_args()
    return args


def print_links(file: TDownloadedFile):
    parser = THtmlParser(file.data)
    links_to_process = list(parser.soup.findAll('a'))
    index = 0
    for l in links_to_process:
        href = l.attrs.get('href')
        if href is not None:
            print("{}: {} {}".format(index, href, l.get_text() ))
        index += 1


def print_text(file: TDownloadedFile):
    parser = THtmlParser(file.data)
    print(parser.get_plain_text())


def print_utf8_html(file: TDownloadedFile):
    print (file.convert_html_to_utf8().lower())


def main():
    logger = setup_logging()
    args = parse_args()
    THttpRequester.initialize(logger)
    for url in args.urls:
        file = TDownloadedFile(url, args.use_cache)
        if args.action == "links":
            print_links(file)
        elif args.action == "text":
            print_text(file)
        elif args.action == "utf8_html":
            print_utf8_html(file)
        else:
            raise Exception ("unknown action")


if __name__ == "__main__":
    main()
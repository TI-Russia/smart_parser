import argparse
import json
import os


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domains",  dest='domains_file', required=True)
    parser.add_argument("--output-folder", dest='folder', required=True)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    domains = list()
    with open(args.domains_file, "r", encoding="utf8") as inpf:
        for domain in inpf:
            domain = domain.strip(" \r\n")
            if len(domain) == 0:
                continue
            with open(os.path.join(args.folder, domain + ".txt"), "w") as outf:
                record = {"sites": [{"morda_url": "http://" + domain}]}
                json.dump(record, outf, indent=4)



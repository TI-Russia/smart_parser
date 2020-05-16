import argparse
import sys
import json
import os
from collections import defaultdict

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
        for x in inpf:
            x = x.strip(" \r\n")
            if len(x) > 0:
                domains.append(x)

    main_domains = defaultdict(set)
    for d in domains:
        items = d.split('.')
        if len(items) == 2:
            main_domains[d].add(d)
        elif len(items) == 3 and d.endswith('gov.ru'):
            main_domains[d].add(d)
    for d in domains:
        if d not in main_domains:
            items = d.split('.')
            print(d)
            assert len(items) > 2
            if d.endswith('gov.ru'):
                main_domain = ".".join(items[-3:])
            else:
                main_domain = ".".join(items[-2:])
            if main_domain in main_domains:
                main_domains[main_domain].add(d)
            else:
                print("cannot find a main domain for a  third level domain: {}".format(d))
                main_domains[d].add(d)

    for main_domain, domains in main_domains.items():
        print("{} -> {}".format(main_domain, ", ".join(domains)))
        with open(os.path.join(args.folder, main_domain+".txt"), "w") as outf:
            sites = list({"morda_url": "http://" + d} for d in domains)
            record = {"sites": sites}
            json.dump(record, outf, indent=4)



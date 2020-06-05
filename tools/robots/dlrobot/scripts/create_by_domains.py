import argparse
import json
import os
import random
import shutil

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domains",  dest='domains_files', required=True,  action="append")
    parser.add_argument("--output-folder", dest='folder', required=True)
    parser.add_argument("--portion-size", dest='portion_count', required=False, default=None, type=int)
    args = parser.parse_args()
    return args


def write_project(output_folder, domain):
    with open(os.path.join(output_folder, domain + ".txt"), "w") as outf:
        record = {"sites": [{"morda_url": "http://" + domain}]}
        json.dump(record, outf, indent=4)


def main():
    args = parse_args()
    domains = set()
    for domains_file in args.domains_files:
        with open(domains_file, "r", encoding="utf8") as inpf:
            for domain in inpf:
                domain = domain.strip(" \r\n")
                if len(domain) == 0:
                    continue
                if domain.find('google.com') != -1 or domain.find('dropbox.com') != -1 or domain.find('yandex.ru') != -1 \
                    or domain.find('yandex.net') != -1:
                    continue
                domains.add(domain)

    domains = list(domains)
    random.shuffle(domains)
    if args.portion_count is None:
        if os.path.exists(args.folder):
            shutil.rmtree(args.folder, ignore_errors=True)
        os.mkdir(args.folder)
        for d in domains:
            write_project(args.folder, d)
    else:
        output_folder = None
        for i in range(len(domains)):
            if i % args.portion_count == 0:
                output_folder = "{}.{:02}".format(args.folder, (int)(i / args.portion_count))
                if os.path.exists(output_folder):
                    shutil.rmtree(output_folder, ignore_errors=True)
                os.mkdir(output_folder)

            write_project(output_folder, domains[i])


if __name__ == "__main__":
    main()



import argparse
import sys
import json
import os
from urllib.parse import urlparse

#cat human2018.txt | jq -cr '.[].url' | shuf | tail -n 30 >30sites/input_urls
#python create_by_urls.py  --input 30sites\input_urls --output-folder 30sites

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", dest='input', required=True)
    parser.add_argument("--output-folder", dest='folder', required=True)
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    domains = set()
    with open(args.input, "r", encoding="utf8") as inpf:
        for x in inpf:
            url = x.strip()
            if len(url) == 0:
                continue
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[len('www.'):]
            domains.add(domain)
            with open(os.path.join(args.folder, domain+".txt"), "w") as outf:
                record = { "sites": [
                    {
                        "morda_url": "http://" + domain
                    }
                ] }
                json.dump(record, outf, indent=4)

    sys.stderr.write("find {} different sites in {}".format(len(domains), args.input))

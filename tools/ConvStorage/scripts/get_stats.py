import logging
import json
from ConvStorage.conversion_client import TDocConversionClient
import argparse
import os
import time

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-file", dest='history_file', default=None)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    conv_client = TDocConversionClient(TDocConversionClient.parse_args([]), logging)
    stats = conv_client.get_stats()
    if args.history_file is None:
        print(json.dumps(stats))
    else:
        lines = list()
        if os.path.exists(args.history_file):
            with open(args.history_file, "r", encoding="utf-8") as inp:
                for l in inp:
                    lines.append(l)
        lines.append("{}\t{}\n".format(int(time.time()), json.dumps(stats)))
        lines = lines[-400:]
        with open(args.history_file, "w", encoding="utf-8") as out:
            for l in lines:
                out.write(l)

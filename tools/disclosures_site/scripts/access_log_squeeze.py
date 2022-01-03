from common.logging_wrapper import setup_logging
from common.access_log import get_human_requests

from collections import defaultdict
import os
import re
import sys
import json
import datetime
import argparse
from urllib.parse import urlparse
from urllib.parse import parse_qs

class TAccessLogReader:

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--action",
            dest="action",
            help="can be build_popular_site_pages, search_stats"
        )
        parser.add_argument(
            "--access-log-folder",
            dest='access_log_folder',
            default="/home/sokirko/declarator_hdd/Yandex.Disk/declarator/nginx_logs/")

        parser.add_argument(
            "--start-access-log-date",
            dest='start_access_log_date',
            default=None,
            help="for example 2021-08-05"
        )

        parser.add_argument(
            "--last-access-log-date",
            dest='last_access_log_date',
            default=None,
            help="for example 2021-08-05"
        )

        parser.add_argument(
            "--min-request-freq",
            dest='min_request_freq',
            default=3,
            help="min freq in access logs"
        )

        parser.add_argument(
            "--output-path",
            dest='output_path',
        )
        return parser.parse_args(arg_list)

    def __init__(self, args):
        self.logger = setup_logging(log_file_name="access_log_reader.log")
        self.args = args
        self.start_access_log_date = self.args.start_access_log_date
        self.last_access_log_date = self.args.last_access_log_date
        self.access_log_folder = self.args.access_log_folder
        self.min_request_freq = self.args.min_request_freq

    def check_date(self, filename):
        (_, date_str, _) = filename.split('.')
        dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')

        if self.start_access_log_date is not None:
            if dt < datetime.datetime.strptime(self.start_access_log_date, '%Y-%m-%d'):
                self.logger.debug("skip {}, it is older than {}".format(filename, self.start_access_log_date))
                return False

        if self.last_access_log_date is not None:
            if dt > datetime.datetime.strptime(self.last_access_log_date, '%Y-%m-%d'):
                self.logger.debug("skip {}, it is newer than {}".format(filename, self.last_access_log_date))
                return False
        return True

    def get_all_log_files(self):
        processed_files_count = 0
        for x in os.listdir(self.access_log_folder):
            if not x.startswith('access'):
                continue
            if not self.check_date(x):
                continue
            processed_files_count += 1
            yield os.path.join(self.access_log_folder, x)
        self.logger.info("processed {} access log files".format(processed_files_count))

    def build_popular_site_pages(self):
        self.logger.info("build_popular_site_pages")
        requests = defaultdict(int)
        for full_path in self.get_all_log_files():
            for r in get_human_requests(full_path, http_status=200):
                match = re.match('^/(section|person)/([0-9]+)/?$', r)
                if match:
                    rec = (match[1].lower(), int(match[2]))
                    requests[rec] += 1
        filtered_by_min_freq = 0
        output_path = self.args.output_path
        self.logger.info("write squeeze to {}".format(output_path))
        with open(output_path, "w") as outp:
            for (record_type, record_id), freq in requests.items():
                if freq < self.min_request_freq:
                    filtered_by_min_freq += 1
                    continue
                record = {
                    'record_id': record_id,
                    'record_type': record_type,
                    'req_freq': freq
                }
                outp.write("{}\n".format(json.dumps(record, ensure_ascii=False)))
        self.logger.info("filtered_by_min_freq({}) = {}".format(self.min_request_freq, filtered_by_min_freq))

    def search_stats(self):
        for full_path in self.get_all_log_files():
            for r in get_human_requests(full_path):
                if r.find('section/?'):
                    parsed_url = urlparse(r)
                    used_params = list()
                    for k,v in parse_qs(parsed_url.query).items():
                        if len(v) > 0 and k != "sort_by":
                            used_params.append(k)
                    used_params.sort()
                    if len(used_params) > 0:
                        print(" ".join(used_params))


def main():
    args = TAccessLogReader.parse_args(sys.argv[1:])
    reader = TAccessLogReader(args)
    if args.action == "build_popular_site_pages":
        reader.build_popular_site_pages()
    elif args.action == "search_stats":
        reader.search_stats()
    else:
        raise Exception("unknonwn action")


if __name__ == "__main__":
    main()


import argparse
import plotly.express as px
import pandas as pd
import datetime
import os
import sys
import json
from collections import defaultdict
import time
import logging

from web_site_db.remote_call import TRemoteDlrobotCallList
from source_doc_http.source_doc_client import TSourceDocClient
#see examples in crontab.txt


def build_html(args, fig, output_file):
    output_file = os.path.join(args.output_folder, output_file)
    fig.write_html(output_file, include_plotlyjs='cdn')


class TDlrobotStats:

    def __init__(self,  args, min_date=None,  min_total_minutes=0):
        self.args = args
        self.min_date = min_date
        self.remote_calls = TRemoteDlrobotCallList(file_name=args.central_stats_file)
        self.cumulative_declaration_files_count = []
        self.cumulative_processed_websites_count = []
        self.end_times = []
        self.end_time_stamps = []
        self.websites = []
        self.total_minutes = []
        self.host_names = []
        self.declaration_files_by_workers = []
        self.exported_files_counts = []
        self.failures = []
        self.failures_by_hostnames = defaultdict(int)
        self.successes_by_hostnames = defaultdict(int)

        self.build_stats(min_date)

    def build_stats(self, min_date=None, min_total_minutes=0):
        min_time_stamp = min_date.timestamp() if min_date is not None else 0;
        website_count = 0
        sum_count = 0
        for remote_call in self.remote_calls:
            if remote_call.end_time is None or remote_call.end_time < min_time_stamp:
                continue
            if remote_call.get_total_minutes() < min_total_minutes:
                continue
            end_time = datetime.datetime.fromtimestamp(remote_call.end_time)
            self.end_times.append(pd.Timestamp(end_time))
            self.end_time_stamps.append(end_time.strftime("%Y-%m-%d %H:%M:%S"))

            self.websites.append(remote_call.get_website())
            self.host_names.append(remote_call.worker_host_name)

            # len (self.declaration_files_by_workers) != len(self.remote_calls)
            self.declaration_files_by_workers.extend([remote_call.worker_host_name] * remote_call.result_files_count)

            self.total_minutes.append(remote_call.get_total_minutes())
            self.exported_files_counts.append(remote_call.result_files_count)

            sum_count += remote_call.result_files_count
            self.cumulative_declaration_files_count.append(sum_count)

            website_count += 1
            self.cumulative_processed_websites_count.append(website_count)
            if remote_call.exit_code != 0:
                self.failures.append(remote_call.worker_host_name)
                self.failures_by_hostnames[remote_call.worker_host_name] += 1
            else:
                self.successes_by_hostnames[remote_call.worker_host_name] += 1

    def write_declaration_crawling_stats(self, html_file):
        df = pd.DataFrame({'Date': self.end_times,
                           "DeclarationFileCount": self.cumulative_declaration_files_count,
                           "website": self.websites})
        title = 'Declaration Count'
        if self.min_date is not None:
            title += " (recent)"
        else:
            title += " (history)"
        fig = px.line(df, x='Date', y='DeclarationFileCount',
                      hover_data=["website"],
                      title=title)
        build_html(self.args, fig, html_file)

    def write_website_progress(self, html_file):
        df = pd.DataFrame({
             'Date': self.end_times,
             "WebSiteCount": self.cumulative_processed_websites_count,
             "website": self.websites})
        title = 'Web Site Progress'
        if self.min_date is not None:
            title += " (recent)"
        else:
            title += " (history)"
        fig = px.line(df, x='Date', y='WebSiteCount', title=title, hover_data=["website"])
        build_html(self.args, fig, html_file)

    def get_project_error_rates(self):
        error_rates = dict()
        for host_name in set (self.host_names):
            f = self.failures_by_hostnames[host_name]
            s = self.successes_by_hostnames[host_name]
            error_rates[host_name] = 100 * (f / (s + f))
        return error_rates


class TDlrobotAllStats:
    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--central-stats-file", dest='central_stats_file', required=False,
                            help="for example /home/sokirko/declarator_hdd/declarator/dlrobot_central/processed_projects/dlrobot_remote_calls.dat")
        parser.add_argument("--conversion-server-stats", dest='conversion_server_stats', required=False,
                            help="for example /home/sokirko/declarator_hdd/declarator/convert_stats.txt")
        parser.add_argument("--central-server-cpu-and-mem", dest='central_server_cpu_and_mem', required=False,
                            help="for example /tmp/glances.dat")
        parser.add_argument("--output-folder", dest='output_folder', required=False, default=".",
                            help="for example ~/smart_parser.disclosures_prod/tools/disclosures_site/disclosures/static")
        return parser.parse_args(arg_list)

    def __init__(self,  args):
        self.args = args

    def build_source_doc_stats(self):
        history_file = "/tmp/source_doc.history"
        if os.path.exists(history_file):
            with open (history_file) as inp:
                history = json.load(inp)
        else:
            history = list()

        source_doc_client = TSourceDocClient(TSourceDocClient.parse_args([]), logger=logging)
        stats = source_doc_client.get_stats()
        now = int(time.time())
        stats['ts'] = now
        history.append(stats)
        while len(history) > 0:
            if now - history[0]['ts'] > 60*60*24: # 24 hours
                history.pop(0)
            else:
                break
        with open (history_file, "w") as out:
            json.dump(history, out)

        timestamps = list()
        source_doc_count = list()
        for l in history:
            dttime = datetime.datetime.fromtimestamp(l['ts'])
            timestamps.append(pd.Timestamp(dttime))
            source_doc_count.append(l['source_doc_count'])

        df = pd.DataFrame({'Time': timestamps, "source_doc_count": source_doc_count})
        fig = px.line(df, x='Time', y='source_doc_count', title='Source Document Count')
        build_html(self.args, fig, "source_doc_count.html")

    def process_dlrobot_stats(self):
        stats = TDlrobotStats(self.args)
        stats.write_declaration_crawling_stats('declaration_crawling_stats.html')
        stats.write_website_progress('file_progress.html')

        min_time = datetime.datetime.now() - datetime.timedelta(hours=12)
        stats12hours = TDlrobotStats(self.args, min_time)
        stats12hours.write_declaration_crawling_stats('declaration_crawling_stats_12h.html')
        stats12hours.write_website_progress('file_progress_12h.html')

        df = pd.DataFrame({'host_names': stats12hours.host_names})
        fig = px.histogram(df, x="host_names", title="Projects By Workers (12 hours)")
        build_html(self.args, fig, "worker_stats_12h.html")

        df = pd.DataFrame({'declaration_files_by_workers': stats12hours.declaration_files_by_workers})
        fig = px.histogram(df, x="declaration_files_by_workers", title="Declaration Files By Workers (12 hours)")
        build_html(self.args, fig, "declaration_files_by_workers_12h.html")

        df = pd.DataFrame({'failures': stats12hours.failures})
        fig = px.histogram(df, x="failures", title="Worker Failures (12 hours)")
        build_html(self.args, fig, "failures_12h.html")

        host2error_rates = stats12hours.get_project_error_rates()
        df = pd.DataFrame({'hostnames': list(host2error_rates.keys()),
                           'error_rate_in_percent': list(host2error_rates.values()),
                           })
        fig = px.bar(df, x='hostnames', y='error_rate_in_percent', title="Dlrobot error rate in percent")
        build_html(self.args, fig, "error_rates_12h.html")

        self.build_source_doc_stats()

    def process_convert_stats(self):
        with open(self.args.conversion_server_stats, encoding="utf8") as inp:
            timestamps = list()
            ocr_pending_all_file_sizes = list()
            for l in inp:
                (timestamp, stats) = l.split("\t")
                dttime = datetime.datetime.fromtimestamp(int(timestamp))
                timestamps.append(pd.Timestamp(dttime))
                ocr_pending_all_file_sizes.append( json.loads(stats)['ocr_pending_all_file_size'])

        df = pd.DataFrame({'Time': timestamps, "ocr_pending_file_sizes": ocr_pending_all_file_sizes})
        fig = px.line(df, x='Time', y='ocr_pending_file_sizes',
                            title='Ocr Conversion Server')
        build_html(self.args, fig, "ocr_pending_file_sizes.html")

    def process_cpu_and_mem_stats(self):
        # input file is built by ~/smart_parser/tools/workstation_monitoring.py
        with open(self.args.central_server_cpu_and_mem) as inp:
            data_points = json.load(inp)
        cpu_stats = list()
        mem_stats = list()
        timestamps = list()
        for x in data_points:
            dttime = datetime.datetime.fromtimestamp(x.pop('ts'))
            timestamps.append(pd.Timestamp(dttime))
            cpu_stats.append(x['cpu'])
            mem_stats.append(x['mem'])

        df = pd.DataFrame({'Time': timestamps, "cpu_stats": cpu_stats, "mem_stats": mem_stats})
        fig = px.line(df, x='Time', y='cpu_stats', title='Dlrobot central cpu(%)')
        build_html(self.args, fig, "dlrobot_central_cpu.html")

        fig = px.line(df, x='Time', y='mem_stats', title='Dlrobot central memory(%)')
        build_html(self.args, fig, "dlrobot_central_mem.html")

    def build_stats(self):
        if self.args.central_stats_file is not None:
            self.process_dlrobot_stats()
        if self.args.conversion_server_stats is not None:
            self.process_convert_stats()
        if self.args.central_server_cpu_and_mem is not None:
            self.process_cpu_and_mem_stats()


if __name__ == "__main__":
    args = TDlrobotAllStats.parse_args(sys.argv[1:])
    TDlrobotAllStats(args).build_stats()

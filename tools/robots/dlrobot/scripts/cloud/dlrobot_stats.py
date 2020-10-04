import argparse
import plotly.express as px
import pandas as pd
import datetime
import os
import json
from remote_call import TRemoteDlrobotCall


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--central-stats-file", dest='central_stats_file', required=False,
                        help="for example /home/sokirko/declarator_hdd/declarator/2020-09-29/processed_projects/dlrobot_remote_calls.dat")
    parser.add_argument("--conversion-server-stats", dest='conversion_server_stats', required=False,
                        help="for example /home/sokirko/declarator_hdd/declarator/convert_stats.txt")
    parser.add_argument("--output-folder", dest='output_folder', required=False, default=".",
                        help="for example ~/smart_parser.disclosures_prod/tools/disclosures/disclosures/static")
    args = parser.parse_args()
    return args


def build_html(args, fig, output_file):
    output_file = os.path.join(args.output_folder, output_file)
    fig.write_html(output_file, include_plotlyjs='cdn')


class TCumulativeStats:
    def __init__(self,  args, min_date=None):
        self.args = args
        self.min_date = min_date
        self.remote_calls = TRemoteDlrobotCall.read_remote_calls_from_file(args.central_stats_file)
        self.cumulative_declaration_files_count = []
        self.cumulative_processed_websites_count = []
        self.end_times = []
        self.websites = []
        self.projects_by_workers = []
        self.declaration_files_by_workers = []
        self.build_stats(min_date)

    def build_stats(self, min_date=None):
        min_time_stamp = min_date.timestamp() if min_date is not None else 0;
        website_count = 0
        sum_count = 0
        for remote_call in self.remote_calls:
            if remote_call.end_time is None or remote_call.end_time < min_time_stamp:
                continue
            dttime = datetime.datetime.fromtimestamp(remote_call.end_time)
            self.end_times.append(pd.Timestamp(dttime))
            self.websites.append(remote_call.get_website())
            self.projects_by_workers.append(remote_call.worker_host_name)
            self.declaration_files_by_workers.extend([remote_call.worker_host_name] * remote_call.result_files_count)

            sum_count += remote_call.result_files_count
            self.cumulative_declaration_files_count.append(sum_count)

            website_count += 1
            self.cumulative_processed_websites_count.append(website_count)

    def write_declaration_crawling_stats(self, html_file):
        df = pd.DataFrame({'Date': self.end_times,
                           "DeclarationFileCount": self.cumulative_declaration_files_count,
                           "website": self.websites})
        title = 'Declaration Crawling Progress'
        if self.min_date is not None:
            title += " start from " + str(self.min_date)
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
            title += " start from " + str(self.min_date)
        fig = px.line(df, x='Date', y='WebSiteCount', title=title, hover_data=["website"])
        build_html(self.args, fig, html_file)


def process_cumulative_stats(args):
    stats = TCumulativeStats(args)
    stats.write_declaration_crawling_stats('declaration_crawling_stats.html')
    stats.write_website_progress( 'file_progress.html')

    min_time = datetime.datetime.now() - datetime.timedelta(hours=12)
    stats = TCumulativeStats(args, min_time)
    stats.write_declaration_crawling_stats('declaration_crawling_stats_12h.html')
    stats.write_website_progress('file_progress_12h.html')

    df = pd.DataFrame({'projects_by_workers': stats.projects_by_workers})
    fig = px.histogram(df, x="projects_by_workers", title="Projects By Workers (12 hours)")
    build_html(args, fig, "worker_stats_12h.html")

    df = pd.DataFrame({'declaration_files_by_workers': stats.declaration_files_by_workers})
    fig = px.histogram(df, x="declaration_files_by_workers", title="Declaration Files By Workers (12 hours)")
    build_html(args, fig, "declaration_files_by_workers_12h.html")


class TPointStats:
    def __init__(self, args):
        self.args = args
        self.remote_calls = TRemoteDlrobotCall.read_remote_calls_from_file(args.central_stats_file)
        self.minutes = []
        self.websites = []
        self.projects_by_workers = []
        self.exported_files_counts = []
        self.end_time_stamps = []
        self.build_stats()

    def build_stats(self):
        for remote_call in self.remote_calls:
            if remote_call.end_time is None:
                continue
            if remote_call.get_total_minutes() < 10:
                continue
            self.minutes.append(remote_call.get_total_minutes())
            self.websites.append(remote_call.get_website())
            self.projects_by_workers.append(remote_call.worker_host_name)
            self.exported_files_counts.append(remote_call.result_files_count)
            end_time = datetime.datetime.fromtimestamp(remote_call.end_time)
            self.end_time_stamps.append(end_time.strftime("%Y-%m-%d %H:%M:%S"))

    def write_stats(self,  html_file):
        df = pd.DataFrame({
            'Minutes': self.minutes,
            "Websites": self.websites,
            "hostnames": self.projects_by_workers,
            "exported_files_counts": self.exported_files_counts,
            'end_times': self.end_time_stamps})

        fig = px.line(df, x='end_times', y='Minutes',
                      hover_data=['Websites', "hostnames", "exported_files_counts", "end_times"],
                      title='Crawl Website Speed')
        build_html(self.args, fig, html_file)


def process_point_stats(args):
    stats = TPointStats(args)
    stats.write_stats('web_site_speed.html')


def process_convert_stats(args):
    with open(args.conversion_server_stats, encoding="utf8") as inp:
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
    build_html(args, fig, "ocr_pending_file_sizes.html")


def main(args):
    if args.central_stats_file is not None:
        process_cumulative_stats(args)
        process_point_stats(args)
    if args.conversion_server_stats is not None:
        process_convert_stats(args)


if __name__ == "__main__":
    args = parse_args()
    main(args)

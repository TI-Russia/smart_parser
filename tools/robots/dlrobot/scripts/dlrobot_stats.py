import argparse
import re
import plotly.express as px
import pandas as pd
import datetime
import os
from glob import glob
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--monitoring-glob", dest='monitoring_glob', required=True,
                        help="for example /home/sokirko/declarator_hdd/processed_projects.[0-9][0-9]/*/*.clicks.stats")
    args = parser.parse_args()
    return args


def get_data(monitoring_glob):
    files = glob(monitoring_glob)
    result = []
    for f in files:
        try:
            with open(str(f), encoding="utf8") as inp:
                m = re.search('"files_count": ([0-9]+),', inp.read())
                if m:
                    files_count = int(m.group(1))
                    mtime = datetime.datetime.fromtimestamp(Path(f).stat().st_mtime)
                    result.append((mtime,  files_count, str(f)))
                else:
                    continue
        except Exception as exp:
            print(exp)
            continue
    result.sort()
    return result


def main(args):
    declarations_count = []
    processed_files_count = []
    timestamps = []
    website = []
    sum = 0
    file_count = 0
    for mtime, value, file_name in get_data(args.monitoring_glob):
        timestamps.append(pd.Timestamp(mtime))
        fname = os.path.basename(file_name)
        if fname.endswith(".txt.clicks.stats"):
            fname = fname[:-len(".txt.clicks.stats")]
        website.append(fname)
        sum += value
        file_count += 1
        declarations_count.append(sum)
        processed_files_count.append(file_count)

    df = pd.DataFrame({'Date': timestamps, "DeclarationCount": declarations_count, "website": website})
    fig = px.line(df, x='Date', y='DeclarationCount',
                        hover_data=["website"],
                        title='Declaration Crawling Progress')
    fig.write_html('declaration_crawling_stats.html')

    df = pd.DataFrame({'Date': timestamps, "FilesCount": processed_files_count, "website": website} )
    fig = px.line(df, x='Date', y='FilesCount',  title='File Progress', hover_data=["website"])
    fig.write_html('file_progress.html')


if __name__ == "__main__":
    args = parse_args()
    main(args)

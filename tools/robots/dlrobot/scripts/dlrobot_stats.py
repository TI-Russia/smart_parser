import argparse
import re
import plotly.express as px
import pandas as pd
from pathlib import Path
import datetime
import os

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--monitoring-folder", dest='monitoring_folder', required=True)
    parser.add_argument("--port", dest='port')
    args = parser.parse_args()
    return args


def get_data(already_processed, folder):
    files = sorted(Path(folder).glob('*/*.clicks.stats'))
    result = []
    for f in files:
        if str(f) in already_processed:
            continue
        try:
            with open(str(f), encoding="utf8") as inp:
                m = re.search('"files_count": ([0-9]+),', inp.read())
                if m:
                    files_count = int(m.group(1))
                    mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
                    result.append((mtime,  files_count, str(f)))
                    already_processed.add(str(f))
                else:
                    continue
        except Exception as exp:
            print(exp)
            continue
    result.sort()
    return result


def main(args):
    already = set()
    declatations_count = []
    processed_files_count = []
    timestamps = []
    texts = []
    hover_texts = []
    while True:
        new = get_data(already, args.monitoring_folder)
        if len(new) == 0:
            break
        sum = 0
        file_count = 0
        for mtime, value, file_name in new:
            timestamps.append(pd.Timestamp(mtime))
            fname = os.path.basename(file_name)
            if fname.endswith(".txt.clicks.stats"):
                fname = fname[:-len(".txt.clicks.stats")]
            if value > 100:
                texts.append(fname)
            else:
                texts.append("")
            hover_texts.append(fname)
            sum += value
            file_count += 1
            declatations_count.append(sum)
            processed_files_count.append(file_count)
    #dates = list(pd.Timestamp(d) for d in ['2020-05-19 14:30', '2020-05-19 15:30', '2020-05-20 1:00'])
    #values = [1, 2, 3]

    df = pd.DataFrame({'Date': timestamps, "DeclarationCount": declatations_count, "text": texts} )
    fig = px.line(df, x='Date', y='DeclarationCount', text="text",  title='Declaration Crawling Progress')
    fig.write_html('declaration_crawling_stats.html')

    df = pd.DataFrame({'Date': timestamps, "FilesCount": processed_files_count, "text": texts} )
    fig = px.line(df, x='Date', y='FilesCount',  title='File Progress')
    fig.write_html('file_progress.html')


if __name__ == "__main__":
    args = parse_args()
    main(args)

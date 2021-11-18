import argparse
import json
import time
import psutil


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-depth", help="forget data that is older than history_depth ", dest="history_depth", type=int, default=5*60*60) # 5 hours
    parser.add_argument("--time-rate", help="time rate for glances",  dest='time_rate', type=int, default=10)
    parser.add_argument("--output-file",  dest='output_file')
    return parser.parse_args()


def main():
    args = parse_args()

    lines = list()
    while True:
        now = time.time()
        rec = {
            'ts': int(now),
            'mem': round(psutil.virtual_memory().percent, 2),
            'cpu': round(float(psutil.cpu_percent()), 2)
        }
        lines.append(rec)
        while len(lines) > 0:
            if now - lines[0]['ts'] > args.history_depth:
                lines.pop()
            else:
                break
        with open(args.output_file, "w") as outp:
            json.dump(lines, outp)
        time.sleep(args.time_rate)


if __name__ == '__main__':
    main()
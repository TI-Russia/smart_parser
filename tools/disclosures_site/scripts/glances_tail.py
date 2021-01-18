import argparse
import json
import subprocess
import time
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-depth", help="forget data that is older than history_depth ", dest="history_depth", type=int, default=5*60*60) # 5 hours
    parser.add_argument("--time-rate", help="time rate for glances",  dest='time_rate', type=int, default=10)
    parser.add_argument("--output-file",  dest='output_file')
    return parser.parse_args()


def run_glances_subprocess(args):
    cmd_args = ['/home/sokirko/.local/bin/glances',
                '--stdout-csv',  'now,mem.used,cpu.user',
                '-t', str(args.time_rate)]
    return subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main():
    args = parse_args()
    glances_proc = run_glances_subprocess(args)
    lines = list()
    while True:
        new_line = glances_proc.stdout.readline().decode('latin').strip()
        if len(new_line) == 0 or 'mem.used' in new_line:
            continue
        time_str, mem_used, user_cpu = new_line.split(',')
        date_time_obj = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S %Z')
        rec = {
            'timestamp': int(date_time_obj.timestamp()),
            'mem': round(float(mem_used) / float(1024*1024*1024), 2),
            'cpu': round(float(user_cpu), 2)
        }
        lines.append(rec)
        now = time.time()
        while len(lines) > 0:
            if now - lines[0]['timestamp'] > args.history_depth:
                lines.pop()
            else:
                break
        with open(args.output_file, "w") as outp:
            json.dump(lines, outp, indent=4)


if __name__ == '__main__':
    main()
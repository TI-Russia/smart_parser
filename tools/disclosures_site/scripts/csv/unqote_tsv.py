import csv
import sys
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--column",  "-c", dest='column')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    for task in csv.DictReader(sys.stdin, delimiter="\t", quotechar='"'):
        print(task[args.column])


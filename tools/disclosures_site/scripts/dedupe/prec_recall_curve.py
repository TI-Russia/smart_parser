from sklearn.metrics import precision_recall_curve
import sys
import optparse

import json
import matplotlib.pyplot as plt


def plot_line(plt, filename, color, ignore_tuned_threshold):
    precision = []
    recall = []
    data = []
    for x in open(filename, "r"):
        j = json.loads(x)
        if ignore_tuned_threshold and j.get("dedupe_recall_weight") is not None:
            continue
        data.append(j)
    data = sorted(data, key=lambda p: p['R'])  # sort by recall
    precision = list(d['P'] for d in data)
    recall = list(d['R'] for d in data)
    plt.plot(recall, precision, marker=color),


def parse_opts():
    optp = optparse.OptionParser()
    optp.add_option('-s', '--skip-tuned-threshold', dest="ignore_tuned_threshold", action="store_true", default=False)
    optp.add_option('-p', '--min-precision', dest="min_precision", type=float, default=0.99)
    (opts, args) = optp.parse_args()
    return opts, args


if __name__ == '__main__':
    opts, args = parse_opts()
    colors = ['o', '+', 'v', '.']
    legend = []
    for x, c in zip(args, colors):
        plot_line(plt, x, c, opts.ignore_tuned_threshold)
        legend.append(x)
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.xlim([0.5, 1.0])
    plt.ylim([opts.min_precision, 1.00])  # precision
    plt.title('2-class Precision-Recall curve')
    plt.legend(legend)
    plt.show()

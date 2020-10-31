#echo "select position, count(*) from declarations_section group  by position "  | mysql -h migalka -D disclosures_db  -u disclosures -pdisclosures    >positions.txt
from robots.common.primitives import normalize_and_russify_anchor_text
import re
from collections import  defaultdict
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-positions", dest='raw_positions', required=True)
    return parser.parse_args()

class TGraphCluster:

    def __init__(self, item, count):
        self.collocs = defaultdict(int)
        item = item.replace('\\n', ' ')
        item = normalize_and_russify_anchor_text(item)
        self.graphematical_key = re.sub('[ -]', '', item).lower()
        self.collocs[item] += count

    def get_total_sum(self):
        return sum(v for v in self.items.values())

    def get_max_item(self):
        best = ""
        max_v = 0
        for k, v in self.collocs.items():
            if v > max_v:
                best = k
                max_v = v
        return best

    def add_cluster(self, c):
        for k,v in c.collocs.items():
            self.collocs[k] += v


if __name__ == '__main__':
    args = parse_args()
    graph_buckets = dict()
    with open (args.raw_positions) as inp:
        for line in inp:
            line = line.strip()
            items = line.split("\t")
            if len(items) == 1:
                continue
            position_str, count = items
            if count == "count(*)":
                continue
            c = TGraphCluster(position_str, int(count))

            if c.graphematical_key in graph_buckets:
                graph_buckets[c.graphematical_key].add_cluster(c)
            else:
                graph_buckets[c.graphematical_key] = c

    for b in graph_buckets.values():
        print ("key={}, best={}".format(b.graphematical_key, b.get_max_item()))
        for k,v in b.collocs.items():
            print ("\t{}\t{}".format(k, v))


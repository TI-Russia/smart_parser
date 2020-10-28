from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
import sys
import argparse


class TElasticIndex:
    def __init__(self, es, index_name):
        self.es = es
        self.dev = index_name + "_dev"
        self.prod = index_name + "_prod"
        self.prod_sav = index_name + "_prod_sav"

    def print_stats(self, title):
        print("{}:\n{}".format(title, self.es.cat.indices(), params={"format": "json"}))

    def index_exists(self, index_name):
        return self.es.indices.exists(index_name)

    def delete_index(self, index_name):
        if self.es.indices.exists(index_name):
            sys.stderr.write("delete {}\n".format(index_name))
            self.es.indices.delete(index_name)

    def document_count(self, index_name):
        return self.es.cat.count(index_name, params={"format": "json"})[0]['count']

    def check(self):
        prod_count = self.document_count(self.prod)
        dev_count = self.document_count(self.dev)
        if prod_count > dev_count:
            raise Exception("index {} contains more document than {}".format(self.prod, self.dev))

    def copy_index(self, from_index, to_index):
        ic = IndicesClient(self.es)
        ic.freeze(from_index)
        sys.stderr.write("copy  {} to  {}\n".format(from_index, to_index))
        ic.clone(from_index, to_index)
        ic.unfreeze(from_index)


def dev_to_prod(indices):
    for index in indices:
        index.check()
        index.delete_index(index.prod_sav)
        index.copy_index(index.prod, index.prod_sav)

    for index in indices:
        index.delete_index(index.prod)
        index.copy_index(index.dev, index.prod)


def undo_dev_to_prod(indices):
    for index in indices:
        assert index.index_exists(index.prod_sav)

    for index in indices:
        index.delete_index(index.prod)
        index.copy_index(index.prod_sav, index.prod)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action",  dest='action', required=True,
                        help="can be dev-to-prod or undo-dev-to-prod")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    es = Elasticsearch()
    indices = list()

    for i in ['declaration_office', 'declaration_sections', 'declaration_file', 'declaration_person']:
        index = TElasticIndex(es, i)
        indices.append(index)
    indices[0].print_stats("Before:")
    if args.action == "dev-to-prod":
        dev_to_prod(indices)
    elif args.action == "undo-dev-to-prod":
        undo_dev_to_prod(indices)
    indices[0].print_stats("After:")
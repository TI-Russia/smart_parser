from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient, ClusterClient
import sys
from django.conf import settings
from django.core.management import BaseCommand


class TElasticIndex:

    def __init__(self, es, index_name, options):
        self.es = es
        self.dev = index_name + "_dev"
        self.prod = index_name + "_prod"
        self.prod_sav = index_name + options.get("backup_index_name_suffix", "_prod_sav")
        self.enable_increase_check = options.get('enable_increase_check', True)
        self.enable_empty_check = options.get('enable_empty_check', True)

    def print_stats(self, title):
        sys.stderr.write("{}:\n{}\n".format(title, self.es.cat.indices(), params={"format": "json"}))

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
        if self.enable_increase_check:
            if prod_count > dev_count:
                raise Exception("index {} contains more document than {}".format(self.prod, self.dev))
        if self.enable_empty_check:
            if dev_count == 0:
                raise Exception("index {} contains no documents".format(self.dev))

    def copy_index(self, from_index, to_index):
        ic = IndicesClient(self.es)
        ic.freeze(from_index)
        sys.stderr.write("copy  {} to  {}\n".format(from_index, to_index))
        ic.clone(from_index, to_index, body={"settings": {"index":{"number_of_replicas": 0}}})
        ic.unfreeze(from_index)
        status = ClusterClient(self.es).health(to_index)['status']
        if status != 'green':
            sys.stderr.write("{}\n".format(ClusterClient(self.es).health(to_index)) )
            raise Exception ("clonned index status {} is not green".format(to_index))


def dev_to_prod(indices):
    for index in indices:
        index.check()

    for index in indices:
        index.delete_index(index.prod)
        index.copy_index(index.dev, index.prod)


def undo_dev_to_prod(indices):
    for index in indices:
        assert index.index_exists(index.prod_sav)

    for index in indices:
        index.delete_index(index.prod)
        index.copy_index(index.prod_sav, index.prod)


def backup_prod(indices):
    for index in indices:
        index.delete_index(index.prod_sav)
        if index.index_exists(index.prod):
            index.copy_index(index.prod, index.prod_sav)


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument("--action",  dest='action', required=True,
                            help="can be dev-to-prod, undo-dev-to-prod, backup-prod, copy_single")
        parser.add_argument("--skip-increase-check",  dest='enable_increase_check', required=False,
                            action="store_false", default=True)
        parser.add_argument("--skip-empty-check",  dest='enable_empty_check', required=False,
                            action="store_true", default=True)
        parser.add_argument("--source-index-name",  dest='source_index_name', required=False,
                            default=None, help="set source index if action=copy_single")
        parser.add_argument("--target-index-name",  dest='target_index_name', required=False,
                            default=None, help="set target index if action=copy_single")
        parser.add_argument("--backup-index-name-suffix",  dest='backup_index_name_suffix', required=False,
                            default="_prod_sav")

    def handle(self, *args, **options):
        es = Elasticsearch()
        if options['action'] == "copy_single":
            assert options['target_index_name'] is not None
            assert options['source_index_name'] is not None
            index = TElasticIndex(es, "dummy", options)
            index.copy_index(options['source_index_name'], options['target_index_name'])
            return

        indices = list()
        for x in settings.ELASTICSEARCH_INDEX_NAMES.values():
            if options.get('index_name_substr') is not None:
                if x.find(options.get('index_name_substr')) == -1:
                    continue
            if x.endswith('_prod'):
                index_name = x[:-5]
            elif x.endswith('_dev'):
                index_name = x[:-4]
            else:
                raise  Exception ("unknown index name {} ".format(x))
            sys.stderr.write("collect index {}\n".format(index_name))
            index = TElasticIndex(es, index_name, options)
            indices.append(index)


        indices[0].print_stats("Before:")
        if options['action'] == "dev-to-prod":
            dev_to_prod(indices)
        elif options['action'] == "undo-dev-to-prod":
            undo_dev_to_prod(indices)
        elif options['action'] == "backup-prod":
            backup_prod(indices)

        indices[0].print_stats("After:")
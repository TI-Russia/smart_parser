import re
import json
from collections import  defaultdict
import argparse
from scripts.pure_positions import TPurePositions
import os,sys
sys.path.append (os.path.join(os.environ.get('RML'), "build/Source/lemmatizer_python"))
import aot
aot.load_morphology(1, False)
import itertools

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-positions", dest='raw_positions', required=True)
    parser.add_argument("--pure-position-file", dest='pure_position_file', required=False, default="pure_positions.txt")
    parser.add_argument("--pure-positions-markup", dest='pure_positions_markup', required=False, default="pure_positions_markup.txt")
    return parser.parse_args()


def normalize_spaces(text):
    text = re.sub(r'\\[ntr]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip('_-,   ;')
    return text


def build_spaceless_hash(text):
    text = text.replace("c", "с").replace("e", "е").replace("o", "о")
    return re.sub('[ -]', '', text).lower()


class TMorphDictionaryFound:
    _morph_found = dict()

    @staticmethod
    def is_in_dictionary(word_form):
        found = TMorphDictionaryFound._morph_found.get(word_form)
        if found is None:
            found = aot.is_in_dictionary(word_form)
            TMorphDictionaryFound._morph_found[word_form] = found
        return found


class TCollocation:
    def __init__(self, text, freq):
        self.text = text
        self.freq = freq
        self.text_normalized_spaces = normalize_spaces(text)
        self.text_spaceless_hash = build_spaceless_hash(self.text_normalized_spaces)
        self.all_words_are_in_dictionary = True
        for w in self.get_words():
            if not TMorphDictionaryFound.is_in_dictionary(w):
                self.all_words_are_in_dictionary = False

    def get_words(self):
        words = self.text_normalized_spaces.split()
        for w in words:
            w = w.strip(",();-")
            if len(w) > 0:
                yield w


class TPunctuationCluster:

    def __init__(self, colloc: TCollocation):
        self.cluster_items = defaultdict(list)
        self.total_sum = 0
        self.have_dictionary_variant = False
        self.add_cluster_item(colloc)
        self.norm = None

    def build_norm(self):
        best = None
        max_freq = 0
        for space_normalized_colloc, colloc_list in self.cluster_items.items():
            sum_freq = 0
            max_freq_in_list = 0
            best_in_list = None
            for c in colloc_list:
                if self.have_dictionary_variant and not c.all_words_are_in_dictionary:
                    continue
                sum_freq += c.freq
                if c.freq > max_freq_in_list:
                    max_freq_in_list = c.freq
                    best_in_list = c

            if sum_freq > max_freq:
                best = best_in_list
                max_freq = sum_freq
        self.norm = best

    def add_cluster_item(self, colloc: TCollocation):
        self.cluster_items[colloc.text_normalized_spaces].append(colloc)
        self.total_sum += colloc.freq
        if colloc.all_words_are_in_dictionary:
            self.have_dictionary_variant = True

    def get_cluster_json(self):
        collocs = list({'c': c.text_normalized_spaces, 'freq': c.freq} for v in self.cluster_items.values() for c in v)
        return {
            'norm': self.norm.text_normalized_spaces,
            'collocs': collocs
        }


class TClusters:
    def __init__(self):
        self.clusters_punct = dict()
        self.clusters_hole = defaultdict()
        self.max_hole_count = 2

    def build_punctuation_clusters(self, collocs):
        self.clusters_punct = dict()
        for colloc in collocs:
            cluster = self.clusters_punct.get(colloc.text_spaceless_hash)
            if cluster is None:
                self.clusters_punct[colloc.text_spaceless_hash] = TPunctuationCluster(colloc)
            else:
                cluster.add_cluster_item(colloc)

        for cluster in self.clusters_punct.values():
            cluster.build_norm()

    @staticmethod
    def can_be_hole(word):
        digit_count = 0
        upper_count = 0
        lower_count = 0
        for c in word:
            if c.isdigit():
                digit_count += 1
            if c.isupper():
                upper_count += 1
            if c.islower():
                lower_count += 1
        # number or title case like "г.Московсвкий", Санкт-Петербург, но не ООО
        return digit_count > 0 or (upper_count > 0 and lower_count > 0)

    def iterate_hole_combinations(self, words):
        def build_pattern(combin):
            words_with_holes = []
            for i in range(0, len(words)):
                if i in combin:
                    words_with_holes.append("_")
                else:
                    words_with_holes.append(words[i])
            return " ".join(words_with_holes)

        if len(words) <= 2:
            return
        holes = set()
        for i in range(1, len(words)):
            if TClusters.can_be_hole(words[i]):
                holes.add(i)
        if len(holes) == 0:
            return
        elif len(holes) <= self.max_hole_count:
            yield build_pattern(holes)
        else:
            for combination in itertools.combinations(holes, self.max_hole_count):
                yield build_pattern(combination)

    def build_clusters_hole(self):
        self.clusters_hole = defaultdict(list)
        for cluster in self.clusters_punct.values():
            words = list(cluster.norm.get_words())
            for pattern in self.iterate_hole_combinations(words):
                self.clusters_hole[pattern].append(cluster)

    def dump_clusters_hole(self):
        for k, l in self.clusters_hole.items():
            if len(l) == 1:
                continue
            print(k)
            for c in l:
                print("\t" + c.norm.text_normalized_spaces)

    def dump_clusters_punct(self):
        for k, cluster in self.clusters_punct.items():
            dump = cluster.get_cluster_json()
            dump['key'] = k
            print(json.dumps(dump, indent=4, ensure_ascii=False))


def read_collocations(filename):
    # read file that was created by command:
    # echo "select position, count(*) from declarations_section group  by position "  | mysql -h migalka -D disclosures_db  -u disclosures -pdisclosures    >positions.txt
    result = list()
    with open (filename) as inp:
        for line in inp:
            line = line.strip()
            items = line.split("\t")
            if len(items) == 1:
                continue
            colloc_str, count = items
            if count == "count(*)":
                continue
            result.append(TCollocation(colloc_str, int(count)))
    return result



if __name__ == '__main__':
    args = parse_args()
    collocs = read_collocations(args.raw_positions)
    #pure_positions = TPurePositions(args)
    #pure_positions.build_pure_positions(collocs)
    #clusters = TClusters()
    #clusters.build_punctuation_clusters(collocs)
    #clusters.build_clusters_hole()
    #clusters.dump_clusters_punct()
    #clusters.dump_clusters_hole()
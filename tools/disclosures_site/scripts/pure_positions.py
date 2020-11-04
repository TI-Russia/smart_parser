import sys
import json
import os
import math
from collections import defaultdict

sys.path.append (os.path.join(os.environ.get('RML'), "build/Source/lemmatizer_python"))
import aot
aot.load_morphology(1, False)


def get_word_forms(lemma, grammems):
    resp = aot.synthesize(lemma, grammems)
    for f in json.loads(resp)['forms']:
        yield f.lower()


def is_position_modifier(text):
    return text.lower() in {'главный', 'гл.',
                            'ведущий',
                            'старший', "ст.", 'cтарший', 'страший',
                            'судебный',
                            'младший',
                            'государственный', 'гос.',
                            'первый', '1-ый',
                            "второй", '2-ой',
                            'оперативный', 'управляющий', 'генеральный', 'исполняющий', 'дежурный',
                            'военный', 'индивидуальный', 'художественный', 'уполномоченный', 'ответственный',
                            'торговый', 'полномочный', 'народный', 'системный', 'исполнительный',
                            'социальный', 'участковый', 'ведуший', 'финансовый', 'постоянный',
                            'коммерческий'
   }


def is_relative_word(text):
    return text in {"муж", "жена", "сын", "дочь", "ребенок", "супруга", "супруг"}

class TPurePositions:
    def __init__(self, args):
        self.filename = args.pure_position_file
        self.markup_file = args.pure_positions_markup
        self.prefix_stats = defaultdict(int)
        self.after_prefix_stats = defaultdict(int)
        self.pure_positions = set()
        self.markup = self.read_markup()

    def read_markup(self):
        markup = dict()
        with open (self.markup_file) as inp:
            for line in inp:
                try:
                    prefix, mark = line.strip().split("\t")
                    markup[prefix] = mark
                except Exception as exp:
                    raise Exception("cannot read line {} from {}".format(line, self.markup_file))
        return markup

    def get_prefix_stats(self, collocs):
        for colloc in collocs:
            words = list(colloc.get_words())
            if len(words) == 0:
                continue
            prefix_len = 1
            if len(words) > 1 and is_position_modifier(words[0]):
                prefix_len += 1
                if len(words) > 2 and is_position_modifier(words[1]):
                    prefix_len += 1

            prefix = " ".join(words[0:prefix_len])
            if is_relative_word(prefix):
                continue

            if len(prefix) > 1:
                self.prefix_stats[prefix.lower()] += colloc.freq

            for i in range(prefix_len, len(words)):
                if len(words[i]) > 1:
                    self.after_prefix_stats[words[i].lower()] += colloc.freq

    def calc_features_and_verdict_one_case(self, prefix, freq_first_pos):
        freq_not_first = self.after_prefix_stats[prefix]
        first_place_is_more_frequent = freq_first_pos > freq_not_first * 2
        found_inanim = False
        found_anim = False

        if prefix.find(' ') == -1:
            for interp in json.loads(aot.lemmatize_json(prefix, False)):
                common_grm = set(interp.get('commonGrammems', '').split(','))
                found_inanim = 'inanim' in common_grm
                found_anim = ('anim' in common_grm) and ('surname' not in common_grm)

        verdict = False
        if freq_first_pos <= 5:
            verdict = False
        elif found_anim:
            verdict = True
        elif first_place_is_more_frequent:
            if found_inanim:
                verdict = False
            else:
                if prefix.find(' ') != -1:
                    verdict = True
        features = map(str,
                       (prefix, freq_first_pos, freq_not_first, first_place_is_more_frequent, found_inanim, found_anim))
        return verdict, features

    def calc_features_and_verdict(self):
        most_freq_prefixes = sorted(((v, k) for k,v in self.prefix_stats.items()), reverse=True)
        self.pure_positions = set()
        with open("features_debug.txt", "w") as outp:
            for freq_first_pos, prefix in most_freq_prefixes:
                verdict, features = self.calc_features_and_verdict_one_case(prefix, freq_first_pos)
                outp.write(str(verdict) + "\t" + "\t".join(features) + "\n")
                if verdict:
                    self.pure_positions.add(prefix)

    def write_pure_positions(self):
        with open (self.filename, "w") as outp:
            for p in self.pure_positions:
                outp.write(p + "\n")

    def get_case_weight(self, prefix):
        return int(math.log2(self.prefix_stats.get(prefix, 0) + 1.0))

    def calc_metrics(self):
        false_positive = 0
        true_positive = 0
        for p in self.pure_positions:
            mark = self.markup.get(p)
            weight = self.get_case_weight(p)
            if mark is not None:
                if mark == "1":
                    true_positive += weight
                else:
                    false_positive += weight
        all_positive = sum(self.get_case_weight(prefix) for prefix, mark in self.markup.items() if mark == "1")
        precision = true_positive / (false_positive + true_positive + 0.000001)
        recall = true_positive / (all_positive + 0.000001)
        f1 = (2 * precision * recall) / (recall + precision)
        return {
            'precision': precision,
            'recall': recall,
            'f1': f1
        }

    def build_pure_positions(self, collocs):
        self.get_prefix_stats(collocs)
        self.calc_features_and_verdict()
        self.write_pure_positions()
        print(json.dumps(self.calc_metrics(), indent=4))
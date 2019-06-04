import sys
from collections import defaultdict
import os
import math
from bigrams import DIGIT_TOKEN, tokenize

FOLDER = "texts"

def find_bigrams(colloc):
  tokens = colloc.split(" ")
  return zip(*[tokens[i:] for i in range(2)])

def collect (folder):
    freq_dict = defaultdict(int)

    for filename in os.listdir(folder):
        if filename.endswith("txt"):
            #print(filename.e)
            for line in open(os.path.join(folder, filename), encoding="utf8"):
                for colloc in line.split(";"):
                    tokens = " ".join(tokenize(colloc))
                    if not tokens.startswith(DIGIT_TOKEN) and len(tokens) > 0:
                        freq_dict[tokens] += 1
                        if tokens.count(" ") > 0:
                            for token in tokens.split (" "):
                                freq_dict[token] += 1
                            for bigr in find_bigrams(tokens):
                                freq_dict[" ".join(bigr)] += 1
    return freq_dict



def write_freq_dict(freq_dict, filename):
    with open (filename, "w", encoding="utf8") as fp:
        items = sorted(freq_dict.items(), key=lambda x: x[1], reverse=True)
        for k, v in items:
            fp.write("\t".join([k, str(v)]) + "\n")


def calc_mi_bigrams(freq_dict):
    mi = defaultdict(float)
    all_words_count = 0.0
    for k, v in freq_dict.items():
        if k.find(' ') == -1:
            all_words_count += v

    for k, v in freq_dict.items():
        tokens = k.split(" ")
        if len(tokens) == 2:
            f1 = freq_dict[tokens[0]] / all_words_count
            f2 = freq_dict[tokens[1]] / all_words_count
            f12 = v / all_words_count
            if f1 == 0 or f2 == 0:
                pass
            mi[k] = int( f12 * math.log( f12 / (f1*f2)) * 1000000)
    return mi




if __name__ == "__main__":
    freq_dict = collect(FOLDER)
    write_freq_dict (freq_dict, "freq_dict.txt")
    write_freq_dict (calc_mi_bigrams(freq_dict), "bigrams.txt")

from collections import defaultdict
import re

DIGIT_TOKEN = "[d]"

def strip_puncts(token):
    token = token.strip(u'﻿ \n\r,!.{}[]()"«»\'')
    token = token.lower()
    token = re.sub("[0-9]+", DIGIT_TOKEN, token)
    return token.strip()

def tokenize(v):
    v = v.strip().lower()
    return  [ t for t in map(strip_puncts, v.split()) if len(t) > 0]

def read_bigrams(filename):
    bigrams = defaultdict(float) 
    
    for line in open (filename, "r", encoding="utf8"):
        c, mi = line.strip().split("\t")
        mi = float(mi)
        if mi > 0:
            bigrams[c] = mi
    return bigrams
        
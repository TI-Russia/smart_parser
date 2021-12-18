import sys
from itertools import  groupby


def read_key_and_values():
    for l in sys.stdin:
        #print (l)
        l = l.strip()
        if len(l) == 0:
            continue
        w1, w2 = l.split("\t")
        yield w1, int(w2)

for k, recs in groupby(read_key_and_values(), key=lambda x: x[0]):
    v = sum(v for k,v in recs)
    print ("{}\t{}".format(k, v))
import sys
from itertools import groupby


def read_key_and_values():
    line_no = 1
    for l in sys.stdin:
        l = l.strip()
        if len(l) == 0:
            continue
        items = l.split("\t")
        if len(items) != 2:
            raise Exception("bad line \"{}\", line_no={}, must be two items delimited by a tabulation char".format(
                l, line_no))

        yield items[0], int(items[1])
        line_no += 1


def main():
    for k, recs in groupby(read_key_and_values(), key=lambda x: x[0]):
        v = sum(v for k,v in recs)
        print("{}\t{}".format(k, v))


if __name__ == "__main__":
    main()
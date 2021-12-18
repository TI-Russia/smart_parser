import argparse
import dawg
import sys

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dawg", dest="dawg")
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    base_dawg = dawg.BytesDAWG()
    base_dawg.load(args.dawg)
    for l in sys.stdin:
        w = l.strip()
        f = base_dawg.get(w)
        if f == None or len(f) == 0:
            print  ("-1")
        else:
            f = int.from_bytes(f[0], 'little')
            print (f)

if __name__ == "__main__":
    main()

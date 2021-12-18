import argparse
import dawg

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", dest="input")
    parser.add_argument("--output", dest="output")
    args = parser.parse_args()
    return args

def read_key_values(inp):
    for l in inp:
        words = l.strip().split("\t")
        if len(words) != 2 or len(words[0]) == 0 or not words[1].isdigit():
            print("bad format lins, skip {}".format(l))
        else:
            word, freq = words[0], int(words[1])
            assert freq < 2**32
            yield words[0], freq.to_bytes(4, byteorder='little')

def main():
    args = parse_args()
    with open(args.input) as inp:
        base_dawg = dawg.BytesDAWG(read_key_values(inp))
        base_dawg.save(args.output)

if __name__ == "__main__":
    main()

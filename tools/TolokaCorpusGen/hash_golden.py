import re
import sys

# normal usage: 
# python hash.py golden_1.tsv >golden_1.tsv.hashed_json

def hashCodeNoSpaces(s):
    h = 0
    s = re.sub(r"[\s():;,\".-]", "", s)
    for c in s:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
    return ((h + 0x80000000) & 0xFFFFFFFF) - 0x80000000;

def hashGoldenTolokaFile(filename):
    lineCount = 0
    with open(filename, "r", encoding="utf8") as inpf:
        for x in inpf:
            items = list(x.split("\t"))
            if len(items) <= 1:
                continue
            if len(items) != 4:
                sys.stderr.write("cannot parse input, line = " + str(lineCount+1));
                exit(1)

            if lineCount == 0:
               hashcode = "GOLDEN:declaration_hashcode";
            else:
               hashcode = str(hashCodeNoSpaces(items[2]))
            items[2] = hashcode;
            line = "\t".join(items)
            yield line
            lineCount += 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for line in hashGoldenTolokaFile(sys.argv[1]):
        sys.stdout.write(line)


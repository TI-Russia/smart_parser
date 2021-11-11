from common.primitives import  build_dislosures_sha256
import sys

if __name__ == '__main__':
    for i in sys.argv[1:]:
        print ("{} -> {}".format(i, build_dislosures_sha256(i)))

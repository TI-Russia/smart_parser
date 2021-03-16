import dbm.gnu as gdbm
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", dest='dbm_file')
    parser.add_argument("--action", dest='action', help="can be print, get")
    parser.add_argument("--key", dest='key', help="key to get")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    with gdbm.open(args.dbm_file, 'r') as db:
        if args.action == "print":
            k = db.firstkey()
            while k is not None:
                print("{}\t{}".format(k.decode('utf8'), db[k].decode('utf8')))
                k = db.nextkey(k)
        else:
            if args.action == "get":
                print(db[args.key].decode('utf8'))



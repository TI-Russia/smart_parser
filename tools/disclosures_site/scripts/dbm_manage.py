import dbm.gnu as gdbm
import argparse
import sys
import zlib


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", dest='dbm_file')
    parser.add_argument("--output-db", dest='output_dbm_file', required=False)
    parser.add_argument("--action", dest='action', help="can be print, get, create, print_keys, copy, print_value_lengths, delete")
    parser.add_argument("--key", dest='key', help="key to get")
    parser.add_argument("--zlib-value", dest='use_zlib', action="store_true", default=False)
    return parser.parse_args()


def read_value(args, db, key):
    if args.use_zlib:
        data = db[key]
        if data == b"no_json_found":
            return data.decode("utf8")
        return zlib.decompress(data).decode('utf8')
    else:
        return db[key].decode('utf8')


if __name__ == '__main__':
    args = parse_args()
    if args.action == "create":
        for line in sys.stdin:
            key, value = line.strip().split("\t")
            with gdbm.open(args.dbm_file, 'c') as db:
                db[key] = value
    elif args.action == "delete":
        with gdbm.open(args.dbm_file, 'w') as db:
            del db[args.key]
    else:
        with gdbm.open(args.dbm_file, 'r') as db:
            if args.action == "print":
                k = db.firstkey()
                while k is not None:
                    value = read_value(args, db, k)
                    print("{}\t{}".format(k.decode('utf8'), value))
                    k = db.nextkey(k)
            elif args.action == "print_value_lengths":
                k = db.firstkey()
                while k is not None:
                    value = read_value(args, db, k)
                    print("{}\t{}".format(k.decode('utf8'), len(value)))
                    k = db.nextkey(k)
            elif args.action == "get":
                value = read_value(args, db, args.key)
                print(value)
            elif args.action == "copy":
                # get rid of old values
                k = db.firstkey()
                with gdbm.open(args.output_dbm_file, "c") as out_db:
                    while k is not None:
                        out_db[k] = db[k]
                        k = db.nextkey(k)
            elif args.action == "print_keys":
                k = db.firstkey()
                while k is not None:
                    print(k.decode('utf8'))
                    k = db.nextkey(k)
            else:
                print("unknown action")



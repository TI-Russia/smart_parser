
import sys
import dbm.gnu as gdbm

if __name__ == "__main__":
    print ("open {} as source doc header".format(sys.argv[1]))
    source_doc_db = gdbm.open(sys.argv[1], "w")
    k = source_doc_db.firstkey()
    while k is not None:
        print("{}\t{}".format(k.decode('utf8'), source_doc_db[k].decode('utf8')))
        k = db.nextkey(k)

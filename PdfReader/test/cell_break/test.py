from unittest import TestCase
from declarator_pdf import read_tsv_table, process_pdf_declarator, write_to_tsv

def localfile(filename):
    import os
    dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join( dir, filename)


class TestCellBreak(TestCase):
    def test(self):
        tables = list()
        tables.append(read_tsv_table(localfile("0.tsv")))
        tables.append(read_tsv_table(localfile("2.tsv")))
        canon_table = read_tsv_table(localfile("result.tsv"))
        main_table = process_pdf_declarator(tables)
        print ("test page cell break")
        write_to_tsv(main_table, "debug.tsv")
        self.assertEqual(main_table, canon_table)

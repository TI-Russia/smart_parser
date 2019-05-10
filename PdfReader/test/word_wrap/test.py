from unittest import TestCase
import camelot
from declarator_pdf import read_tsv_table, process_pdf_declarator, get_page_tables, write_to_tsv

def localfile(filename):
    import os
    dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join( dir, filename)


class TestWordWrap(TestCase):
    def test(self):
        tables = camelot.read_pdf(localfile("2018.pdf"), "all", suppress_stdout=True)
        tables = get_page_tables(t.df for t in tables._tables)
        main_table = process_pdf_declarator(tables)
        canon_table = read_tsv_table(localfile("result.tsv"))
        write_to_tsv(main_table, "debug.tsv")
        self.assertEqual(main_table, canon_table)

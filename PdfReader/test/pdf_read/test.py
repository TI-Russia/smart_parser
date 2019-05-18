from unittest import TestCase
from declarator_pdf import read_tsv_table, TTableJoiner, get_page_tables, write_to_tsv, camelot_read_pdf

def localfile(filename):
    import os
    dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join( dir, filename)


class TestSingleLine(TestCase):
    def test(self):
        tables = camelot_read_pdf(localfile("test.pdf"))
        tables.export(localfile('debug.html'), f='html', compress=False)
        tables = get_page_tables(t.df for t in tables._tables)
        main_table = TTableJoiner(tables).process_pdf_declarator()
        canon_table = read_tsv_table(localfile("result.tsv"))
        write_to_tsv(main_table, localfile("debug.tsv"))

        self.assertEqual(main_table, canon_table)

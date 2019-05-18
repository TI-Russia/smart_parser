import camelot
import csv
import os
import re
import argparse
from collections import defaultdict
from collocs.bigrams import tokenize, read_bigrams

VERBOSE = False
BIGRAMS_FILE = os.path.join( os.path.dirname(os.path.abspath(__file__)), "collocs/bigrams.txt")
BIGRAMS = read_bigrams(BIGRAMS_FILE) if os.path.exists(BIGRAMS_FILE) else defaultdict(float)

def delete_thrash_chars(v):
    # убираем все переносы, хотя может случиться, что перенос идет по дефису, например, гараж-бокс
    v = re.sub(u"([а-я])(- *\n *)", r"\1", v)
    v = v.replace ("\n", "\\n")
    v = v.strip()
    if v == "-":
        return ""
    return v

def prettify_strings(table):
    for r in table:
        for i in range(len(r)):
            r[i] = r[i].replace("\\n", " ")
            r[i] = " ".join(r[i].split())
    return table


def read_tsv_table(filename):
    with open(filename, "r", newline='\n', encoding="utf8") as input_stream:
        table = []
        for line in csv.reader(input_stream, delimiter="\t"):
            table.append (line)
    return table


def write_to_tsv(body, filename):
    with open(filename, "w", newline='\n', encoding="utf8") as csv_file:
        writer = csv.writer(csv_file, delimiter='\t')
        for line in body:
            writer.writerow(line)


def write_to_html(body, filename):
    with open(filename, "w", newline='\n', encoding="utf8") as out_file:
        out_file.write("<html><table border=1>\n")
        for line in body:
            s = "<tr><td>{}</td></tr>".format("</td><td>\n".join(line))
            out_file.write(s)
        out_file.write("</table></html>\n")


def add_subheader(header, sub_header):
    if header is None:
        return sub_header
    assert (len(header) == len (sub_header))
    new_header = list()
    for i in range(len(sub_header)):
        new_value = header[i]
        if sub_header[i] != "":
            for k in range(i, 0, -1):
                if header[k] != "":
                    new_value = header[k] + " " + sub_header[i]
                    break
            assert (k > 0)
        new_header.append (new_value)
    return new_header


def glue_to_the_last_row(last_row, row):
    for k in range(len(last_row)):
        if row[k] != "":
            last_row[k] = last_row[k] + " " + row[k]


def check_single_value_in_row(row):
    if len(list(x for x in row if x != "")) <= 1:
        return True
    return False


def check_depended_columns(row, depended_columns):
    for i in range(1, len(row)):
        if row[i] != "" and i in depended_columns and row[i - 1] == "":
            if VERBOSE:
                print(u"found a depended column index={} value={}".format(i, row[i]))
            return True
    return False

def check_bigrams(row, last_row):
    if  len(row) != len (last_row):
        return False
    for i in range(len(row)):
        tokens1 = tokenize(last_row[i])
        tokens2 = tokenize(row[i])
        if len(tokens1) > 0 and len(tokens2) > 0:
            bigram = " ".join([tokens1[-1], tokens2[0]])
            if BIGRAMS[bigram] > 0:
                return True
    return False


def check_merge_predicates(row, depended_columns, last_row):
    return (check_depended_columns(row, depended_columns) or
        check_single_value_in_row(row) or
        check_bigrams (row, last_row));


def find_column(row, word):
    for i in range(len(row)):
        if row[i].lower().find(word) != -1:
            return i
    return -1;

def replace_eolns(s):
    s.replace ('\\n', ' ')
    return s

def is_empty_row(s):
    if len(s) == 0:
        return True
    for x in s:
        if len(x) > 0:
            return False
    return True

class TTableJoiner:
    def __init__(self, tables, verbose=False):
        global VERBOSE
        if verbose:
            VERBOSE = True
        self.title_lines = []
        assert (len(tables) > 0)
        self.tables = tables
        self.move_single_column_rows_to_title()
        first_row = self.tables[0][0]
        self.has_person_index = first_row[0].startswith(u'№')
        self.occupation_column = find_column(first_row, u"должность")
        self.fio_column = find_column(first_row, u"фамилия")
        self.break_by_eolns =  self.check_eoln_format()
        self.detect_header()
        self.build_depended_columns()

    def check_eoln_format(self):
        if self.fio_column == -1:
            return False
        for row in self.tables[0]:
            fio_value = row[self.fio_column].lower()
            lines = fio_value.split("\\n")
            first_line_not_relative = False
            for i in range(len(lines)):
                if i == 0:
                    first_line_not_relative = lines[i].find(u"супруг") == -1
                else:
                    if first_line_not_relative and (lines[i].find(u"супруг") != -1):
                        return True
        return False


    def move_single_column_rows_to_title(self):
        new_table = []
        title_lines = []
        for row in self.tables[0]:
            if len(row) == 1:
                self.title_lines.append(row[0])
            elif len(row[0]) > 30 and row[1] == '':
                self.title_lines.append(row[0])
            else:
                new_table.append (row)
        self.tables[0] = new_table

    def add_or_glue(self, row, body, can_glue=False):
        if len(body) == 0:
            can_glue = False
        if can_glue and check_merge_predicates(row, self.depended_columns, body[-1]):
            if VERBOSE:
                row_str = "\t".join(row)
                print("add line to the prev page: " + row_str)

            if self.has_person_index and row[0] != "":
                if VERBOSE:
                    print("skip joining because the first cell is not empty: " + row[0])
                body.append(list(row))
            else:
                assert (len(body) > 0)
                glue_to_the_last_row(body[len(body) - 1], row)
        else:
            body.append(list(row))

    def build_depended_columns(self):
        null_and_value_bigrams = defaultdict(int)
        value_unigrams = defaultdict(int)
        max_row = 0
        rows_count = 0
        for table in self.tables:
            for row in table[1:]:
                for i in range(1, len(row)):  # ignore the first line, it can contain errors
                    if row[i] != "":
                        if row[i - 1] == "":
                            null_and_value_bigrams[i] += 1
                        value_unigrams[i] += 1
                    max_row = max(i, max_row)
                rows_count += 1

        self.depended_columns = set()
        min_level = 0.05
        for i in range(1, max_row):
            if value_unigrams[i] >= 3:
                level = float(null_and_value_bigrams[i]) / value_unigrams[i]
                if level < min_level:  # fuzzy comparing for typos
                    self.depended_columns.add(i)
                    if VERBOSE:
                        print(
                            "set column {} as depended ({} / {} < {})".format(i, null_and_value_bigrams[i], rows_count,
                                                                              min_level))
        if VERBOSE:
            print ("depended columns:" + str(self.depended_columns))

    def detect_header(self):
        self.header = None
        header_lines_count = 0
        for row in self.tables[0]:
            first_cell = row[0].strip()
            if self.has_person_index:
                if len(first_cell) > 0 and first_cell[0].isdigit():
                    break
            elif header_lines_count > 0 and len(first_cell) > 0:
                break
            self.header = add_subheader(self.header, row)
            header_lines_count += 1
            assert (header_lines_count <= 2)
        self.tables[0][0:header_lines_count] = [] # delete header
        if VERBOSE:
            print ("header:" + str(self.header))


    def add_person_index(self, body):
        if self.has_person_index or self.occupation_column ==  -1:
            return
        self.header.insert(0, u"№")
        person_index = 1
        for row in body:
            if row[self.occupation_column] != '':
                row.insert(0, str(person_index))
                person_index += 1
            else:
                row.insert(0, '')

    def divide_by_eoln(self, united_row, body):
        rows = []
        matrix = list()
        for value in tuple(united_row[1:]):
            matrix.append (list(map(delete_thrash_chars, value.split("\\n"))))

        max_lines_count = max (len(l) for l in matrix)
        for l in matrix:
            for i  in range (len(l), max_lines_count):
                l.append('')

        # transpose matrix by eoln
        matrix = [[matrix[j][i] for j in range(len(matrix))] for i in range(len(matrix[0]))]

        for i in range(len(matrix)):
            row = matrix[i]
            if self.has_person_index:
                row.insert(0, '')
            can_glue = i > 0 and row[self.fio_column] == ""
            self.add_or_glue(row, body, can_glue)


    def process_pdf_declarator(self):
        body = []
        table_no = 0
        for table in self.tables:
            if VERBOSE:
                print ("Table: {}".format(table_no))
                table_no += 1
            table_row_no = 0
            for row in table:
                if self.break_by_eolns:
                    self.divide_by_eoln(row, body)
                else:
                    self.add_or_glue(row, body, (table_row_no == 0))
                table_row_no += 1
        self.add_person_index(body)
        out_table = [self.header] + body
        return prettify_strings([self.header] + body)


def get_page_tables(dataframes):
    tables = list()
    for df  in dataframes:
        table = []
        for row in df.itertuples():
            row = list(map(delete_thrash_chars, tuple(row)[1:]))
            if not is_empty_row(row):
                table.append (row)
        tables.append (table)
    return tables


def write_page_tables(tables):
    for x in range(len(tables)):
        write_to_tsv(tables[x], str(x) + ".tsv")


def parse_args():
    parser = argparse.ArgumentParser(description='Process pdfs for declarator')
    parser.add_argument('-i', '--input', dest='input', nargs='+', help='input files')
    parser.add_argument('--output-tsv', dest="output_tsv", default=None)
    parser.add_argument('--output-html', dest="output_html", default=None)
    parser.add_argument('-p', '--pages', dest="pages", default="all")
    parser.add_argument('-v', '--verbose', dest="verbose", default=False, action="store_true")
    parser.add_argument('--dont-split-text', dest="split_text", default=True, action="store_false")
    parser.add_argument('--write-pages-tsv', dest="write_pages_tsv", default=False, action="store_true")
    parser.add_argument('--bigrams', dest="bigrams_file", default=BIGRAMS_FILE)
    return parser.parse_args()


def camelot_read_pdf(filename, pages="all", split_text=True):
    return camelot.read_pdf(filename, pages,
                              suppress_stdout=True,
                              split_text=split_text,
                              line_scale=40,
                              #shift_text=[''],
                              #line_tol=5,
                              layout_kwargs={'detect_vertical': False}
                            )


def camelot_read_pdf_baseline(filename, pages="all", split_text=True):
    return camelot.read_pdf(filename, pages,
                              suppress_stdout=True,
                              split_text=split_text,
                              line_scale=40,
                              layout_kwargs={'detect_vertical': False})


if __name__ == "__main__":
    args = parse_args()
    VERBOSE = args.verbose
    BIGRAMS = read_bigrams(args.bigrams_file)
    for filename in args.input:
        tables = camelot_read_pdf(filename, args.pages, args.split_text)
        if len(tables._tables) == 0:
            sys.exit(1)
        tables = get_page_tables(t.df for t in tables._tables)
        if len(tables) == 0 or len(tables[0]) == 0:
            print ("No table found, possibly ocr needed")
            sys.exit(1)
        if args.write_pages_tsv:
            write_page_tables(tables)
        main_table = TTableJoiner(tables).process_pdf_declarator ()
        if args.output_tsv is not None:
            write_to_tsv (main_table, args.output_tsv)
        if args.output_html is not None:
            write_to_html (main_table, args.output_html)

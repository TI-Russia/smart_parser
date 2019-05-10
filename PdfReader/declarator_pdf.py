import camelot
import csv
import re
import argparse
from collections import defaultdict

VERBOSE = False

def delete_thrash_chars(v):
    # убираем все переносы, хотя может случиться, что перенос идет по дефису, например, гараж-бокс
    v = re.sub("- *\n *", "", v)
    v = v.replace ("\n", " ")
    v = v.strip()
    if v == "-":
        return ""
    return v


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


def join_to_the_last_row(last_row, row):
    for k in range(len(last_row)):
        if row[k] != "":
            last_row[k] = last_row[k] + " " + row[k]


def try_single_value_in_row(row):
    if len(list(x for x in row if x != "")) <= 1:
        return True
    return False


def try_depended_columns(row, depended_columns):
    for i in range(1, len(row)):
        if row[i] != "" and i in depended_columns and row[i - 1] == "":
            if VERBOSE:
                print(u"found a depended column index={} value={}".format(i, row[i]))
            return True
    return False


def find_position_column(row):
    for i in range(len(row)):
        if row[i].lower().find(u"должность") != -1:
            return i
    return -1;

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
        self.position_column = find_position_column(first_row)

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

    def try_to_merge_to_the_last_row(self, body, row, depended_columns):
        if (try_depended_columns(row, depended_columns) or
                try_single_value_in_row(row)):
            if VERBOSE:
                row_str = "\t".join(row)
                print("add line to the prev page: " + row_str)

            if self.has_person_index and row[0] != "":
                if VERBOSE:
                    print("skip joining because the first cell is not empty: " + row[0])
                return False
            assert (len(body) > 0)
            join_to_the_last_row(body[len(body) - 1], row)
            return True
        return False

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

        depended_columns = set()
        min_level = 0.05
        for i in range(1, max_row):
            if value_unigrams[i] >= 3:
                level = float(null_and_value_bigrams[i]) / value_unigrams[i]
                if level < min_level:  # fuzzy comparing for typos
                    depended_columns.add(i)
                    if VERBOSE:
                        print(
                            "set column {} as depended ({} / {} < {})".format(i, null_and_value_bigrams[i], rows_count,
                                                                              min_level))
        return depended_columns

    def find_header(self):
        header = None
        header_lines_count = 0
        for row in self.tables[0]:
            first_cell = row[0].strip()
            if self.has_person_index:
                if len(first_cell) > 0 and first_cell[0].isdigit():
                    break
            elif header_lines_count > 0 and len(first_cell) > 0:
                break
            header = add_subheader(header, row)
            header_lines_count += 1
            assert (header_lines_count <= 2)
        self.tables[0][0:header_lines_count] = [] # delete header
        return header

    def add_person_index(self, header, body):
        if self.has_person_index or self.position_column ==  -1:
            return
        header.insert(0, u"№")
        person_index = 1
        for row in body:
            if row[self.position_column] != '':
                row.insert(0, str(person_index))
                person_index += 1
            else:
                row.insert(0, '')

    def process_pdf_declarator(self):
        body = []
        header = self.find_header()
        depended_columns = self.build_depended_columns()
        if VERBOSE:
            print ("header:" + str(header))
            print ("depended columns:" + str(depended_columns))
        table_no = 0
        for table in self.tables:
            if VERBOSE:
                print ("Table: {}".format(table_no))
                table_no += 1
            table_row_no = 0
            for row in table:
                if table_row_no > 0 or not self.try_to_merge_to_the_last_row(body, row, depended_columns):
                    body.append (list(row))
                table_row_no += 1
        self.add_person_index(header, body)
        return [header] + body


def get_page_tables(dataframes):
    tables = list()
    for df  in dataframes:
        table = []
        for row in df.itertuples():
            row = list(map(delete_thrash_chars, tuple(row)[1:]))
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
    parser.add_argument('--write-pages-tsv', dest="write_pages_tsv", default=False, action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    VERBOSE = args.verbose
    for x in args.input:
        #tables = camelot.read_pdf(x, args.pages, suppress_stdout=True)
        tables = camelot.read_pdf(x, args.pages, suppress_stdout=True, split_text=True)

        tables = get_page_tables(t.df for t in tables._tables)
        if args.write_pages_tsv:
            write_page_tables(tables)
        main_table = TTableJoiner(tables).process_pdf_declarator ()
        if args.output_tsv is not None:
            write_to_tsv (main_table, args.output_tsv)
        if args.output_html is not None:
            write_to_html (main_table, args.output_html)

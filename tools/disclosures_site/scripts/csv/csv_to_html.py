import sys

if __name__ == "__main__":
    lines = list()
    cols_count = None
    row_count = 0
    for line in sys.stdin:
        line = line.strip("\n\r")
        if len(line) == 0:
            if row_count > 0:
                row_count = 0
                cols_count = None
                print("</table>\n")
            continue
        items = line.split("\t")
        if cols_count is None:
            cols_count = len(items)
        else:
            assert len(items) == cols_count
        if row_count == 0:
            print ("<table class=\"solid_table\">")
            print ("<tr><th>{}</th></tr>".format("</th><th>".join(items)))
        else:
            print("<tr><td>{}</td></tr>".format("</td><td>".join(items)))
        row_count += 1

    if row_count > 0:
        print("</table>")

import re
import sys

if __name__ == "__main__":
    if len(sys.argv) == 1:
        input_stream = sys.stdin
    else:
        input_stream = open(sys.argv[1])
    page_fetched_count = 0.0 + 0.0000000001
    good_files = 0.0
    for x in input_stream:
        x = x.strip()
        mo = re.match('.*(find_links_in_html_by_text|find_links_with_selenium)\s+url=([^ ]+) .*', x)
        if mo:
            page_fetched_count += 1.0
        mo = re.match('.*exported\s+([0-9]+)\s+files.*', x)
        if mo:
            good_files = float(mo.group(1))
    print ("robot efficiency={:.4f}".format(good_files/page_fetched_count))
    if len(sys.argv) > 1:
        input_stream.close()

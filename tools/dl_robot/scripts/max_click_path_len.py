import sys
import json

for file_path in sys.argv[1:]:

    max_path_len = 0
    with open(file_path) as inp:
        for decl_info in json.load(inp):
            click_path = decl_info['click_path']
            max_path_len = max(max_path_len, len(click_path))
    print("{}\t{}".format(file_path, max_path_len))
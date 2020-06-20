from declarations.input_json_specification import dhjs
import json
import sys
import os
from collections import defaultdict

if __name__ == '__main__':
    with open (sys.argv[1], "r") as inp:
        dlrobot_human = json.load(inp)
    website_count = 0
    files_count = 0
    both_found = 0
    only_dlrobot = 0
    only_human = 0
    old_dlrobot = 0
    extensions = defaultdict(int)
    if dhjs.file_collection in dlrobot_human:
        web_sites = dlrobot_human[dhjs.file_collection]
    else:
        web_sites = dlrobot_human

    for web_site_info in web_sites.values():
        website_count += 1
        for file_info in web_site_info.values():
            files_count += 1
            if file_info[dhjs.intersection_status] == dhjs.both_found:
                both_found += 1
            if file_info[dhjs.intersection_status] == dhjs.only_dlrobot:
                only_dlrobot += 1
            if file_info[dhjs.intersection_status] == dhjs.only_human:
                only_human += 1
            if file_info.get(dhjs.dlrobot_copied_from_the_past, False):
                old_dlrobot += 1
            file_path = file_info.get(dhjs.dlrobot_path, file_info.get("dlrobot_path"))
            if file_path is None:
                print("file record has no file path member: {}".format(file_info))
                sys.exit(1)
            filename, extension = os.path.splitext(file_path)
            extensions[extension] += 1


    stats = {
        "web_sites_count": website_count,
        "files_count": files_count,
        "both_found": both_found,
        "only_human": only_human,
        "only_dlrobot": only_dlrobot,
        "old_dlrobot(not found in this run)": old_dlrobot,
        "extensions": dict(extensions),
    }
    print (json.dumps(stats, indent=4)  )

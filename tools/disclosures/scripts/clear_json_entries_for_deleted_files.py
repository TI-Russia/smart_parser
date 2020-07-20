from declarations.input_json_specification import dhjs
import json
import sys
import os


if __name__ == '__main__':
    json_file_name = sys.argv[1]
    with open(json_file_name, "r") as inp:
        dlrobot_human = json.load(inp)

    main_folder = os.path.join( os.path.dirname(json_file_name), dlrobot_human[dhjs.dlrobot_folder])
    print ("main folder: {}".format(main_folder))
    cnt = 0
    print ("process {} web sites".format(len(dlrobot_human[dhjs.file_collection].keys())))
    for web_site, web_site_info in dlrobot_human[dhjs.file_collection].items():
        to_remove = set()
        for sha256, file_info in web_site_info.items():
            file_path = file_info.get(dhjs.dlrobot_path)
            if file_path is None:
                print("file record has no file path member: {}".format(file_info))
                sys.exit(1)
            path = os.path.join(main_folder, web_site, file_path)
            if not os.path.exists(path):
                print("remove json entry for {}".format(path))
                to_remove.add(sha256)
                cnt += 1
        for sha256 in to_remove:
            del web_site_info[sha256]

    print("removed {} entries".format(cnt))

    with open(json_file_name, "w") as out:
        out.write(json.dumps(dlrobot_human, indent=4))

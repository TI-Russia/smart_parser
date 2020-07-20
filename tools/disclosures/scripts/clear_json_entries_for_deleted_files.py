import sys
import os
from declarations.input_json import TDlrobotHumanFile


if __name__ == '__main__':
    json_file_name = sys.argv[1]
    dlrobot_human = TDlrobotHumanFile(input_file_name=json_file_name)
    to_remove = set()
    for sha256, src_doc in dlrobot_human.document_collection.items():
        path = dlrobot_human.get_document_path(src_doc, absolute=True)
        if not os.path.exists(path):
            print("remove json entry for {}".format(path))
            to_remove.add(sha256)

    for sha256 in to_remove:
        del dlrobot_human.document_collection[sha256]

    print("removed {} entries".format(len(to_remove)))
    dlrobot_human.write(json_file_name)

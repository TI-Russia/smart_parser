from declarations.input_json_specification import dhjs
import json
import sys
from declarations.models import  SPJsonFile

if __name__ == '__main__':
    with open (sys.argv[1], "r") as inp:
        dlrobot_human = json.load(inp)
    files_count = 0
    if dhjs.file_collection in dlrobot_human:
        web_sites = dlrobot_human[dhjs.file_collection]
    else:
        web_sites = dlrobot_human

    for web_site_info in web_sites.values():
        for sha256, file_info in web_site_info.items():
            file = SPJsonFile.objects.filter(sha256=sha256).all()[:1].get()
            if file is None:
                print("cannot find file with sha256={}".format(sha256))
            else:
                declarator_document_file_url = file_info.get(dhjs.declarator_document_file_url)
                if declarator_document_file_url is not None:
                    file.declarator_document_file_url = declarator_document_file_url

                dlrobot_url = file_info.get(dhjs.dlrobot_url)
                if dlrobot_url is not None:
                    file.dlrobot_url = dlrobot_url
                file.save()
                files_count += 1

    print("updated {} record in db".format(files_count))

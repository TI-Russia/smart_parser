import json
import sys
import os
from collections import defaultdict
from declarations.serializers import  TDlrobotHumanFile, TWebReference
from declarations.input_json import TIntersectionStatus

if __name__ == '__main__':
    dlrobot_human = TDlrobotHumanFile(input_file_name=sys.argv[1])
    websites = set()
    files_count = 0
    both_found = 0
    only_dlrobot = 0
    only_human = 0
    extensions = defaultdict(int)
    crawl_epochs = defaultdict(int)

    for src_doc in dlrobot_human.document_collection.values():
        websites.add(src_doc.get_web_site())
        files_count += 1
        if src_doc.intersection_status == TIntersectionStatus.both_found:
            both_found += 1
        if src_doc.intersection_status == TIntersectionStatus.only_dlrobot:
            only_dlrobot += 1
        if src_doc.intersection_status == TIntersectionStatus.only_human:
            only_human += 1
        for ref in src_doc.references:
            if isinstance(ref, TWebReference):
                crawl_epochs[ref.crawl_epoch] += 1
        _, extension = os.path.splitext(src_doc.document_path)
        extensions[extension] += 1


    stats = {
        "web_sites_count": len(websites),
        "files_count": files_count,
        "both_found": both_found,
        "only_human": only_human,
        "crawl_epochs": dict(crawl_epochs),
        "extensions": dict(extensions),
    }
    print (json.dumps(stats, indent=4)  )

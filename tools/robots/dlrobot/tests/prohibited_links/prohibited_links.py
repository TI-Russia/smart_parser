from robots.common.find_link import web_link_is_absolutely_prohibited
from robots.common.download import TDownloadEnv
import sys

if __name__ == "__main__":
    TDownloadEnv.clear_cache_folder()

    #gfind ../../regression_tests/tests.sav.2020-04-17 -name '*.log'  | xargs -n 1 python scripts/collect_cross_domain_links.py   | sort | uniq >cross_domain.txt
    for x in open(sys.argv[1]):
        source, target = x.strip().split("\t")
        res = web_link_is_absolutely_prohibited(source, target)
        res_str = "bad_link" if res else "good_link"
        print ("\t".join((res_str, source, target)))

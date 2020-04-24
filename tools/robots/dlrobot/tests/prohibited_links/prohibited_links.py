import sys
from robots.common.find_link import web_link_is_absolutely_prohibited

if __name__ == "__main__":
    #gfind ../../regression_tests/tests.sav.2020-04-17 -name '*.log'  | xargs -n 1 python collect_cross_domain_links.py   | sort | uniq >cross_domain.txt
    for x in open ("cross_domain.txt"):
        source, target = x.strip().split("\t")
        res = web_link_is_absolutely_prohibited(source, target)
        print ("\t".join((str(res), source, target)))

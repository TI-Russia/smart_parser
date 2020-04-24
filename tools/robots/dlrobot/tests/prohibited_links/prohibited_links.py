import sys
from robots.common.find_link import web_link_is_absolutely_prohibited

mirror_examples = [
    ("www.mvd.ru", "www.yandex.ru"),
    ("mvd.ru", "мвд.рф"),
    ("www.mvd.ru", "mvd.ru"),
    ("www.mvd.ru", "www.mvd.ru/print=1"),
]

if __name__ == "__main__":
    for d1,d2 in mirror_examples:
        res = web_link_is_absolutely_prohibited(d1, d2)
        print ("\t".join((str(not res), d1, d2)))

    #gfind ../../regression_tests/tests.sav.2020-04-17 -name '*.log'  | xargs -n 1 python collect_cross_domain_links.py   | sort | uniq >cross_domain.txt
    for x in open ("cross_domain.txt"):
        source, target = x.strip().split("\t")
        res = web_link_is_absolutely_prohibited(source, target)
        print ("\t".join((str(not res), source, target)))

from robots.common.find_link import web_link_is_absolutely_prohibited
from robots.common.download import TDownloadEnv, TDownloadedFile
import sys

if __name__ == "__main__":
    TDownloadEnv.clear_cache_folder()

    #2020-09-19  "мвд.рф" is out of reach
    #downloaded_file = TDownloadedFile("мвд.рф")
    #assert len(downloaded_file.data) > 0
    for x in open(sys.argv[1]):
        source, target = x.strip().split("\t")
        res = web_link_is_absolutely_prohibited(source, target)
        res_str = "bad_link" if res else "good_link"
        print ("\t".join((res_str, source, target)))

import re
import sys
from urllib.parse import urlparse, unquote


def get_site_domain_wo_www(url):
    url = "http://" + url.split("://")[-1]
    domain = urlparse(url).netloc
    if domain.startswith('www.'):
        domain = domain[len('www.'):]
    return domain


if __name__ == "__main__":
    source_url = ""
    for x in open(sys.argv[1]):
        x = x.strip()
        mo = re.match('.*(find_links_in_html_by_text|find_links_with_selenium)\s+url=([^ ]+) .*', x)
        if mo:
            source_url = get_site_domain_wo_www(mo.group(2))
        mo = re.match('.*add link ([^ ]+).*', x)
        if mo:
            add_link = get_site_domain_wo_www(mo.group(1))
            equ_domain = (add_link == source_url)
            if not equ_domain:
                print("\t".join((source_url,add_link)))

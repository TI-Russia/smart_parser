import urllib.parse
import re
from common.link_info import TLinkInfo
import socket


def strip_viewer_prefix(href):
    if href is None:
        return href
    # https://docs.google.com/viewer?url=https%3A%2F%2Foren-rshn.ru%2Findex.php%3Fdo%3Ddownload%26id%3D247%26area%3Dstatic%26viewonline%3D1
    viewers = ['https://docs.google.com/viewer?url=',
                'https://docviewer.yandex.ru/?url=',
                'https://view.officeapps.live.com/op/embed.aspx?src=',
                'https://view.officeapps.live.com/op/view.aspx?src=']
    for prefix in viewers:
        if href.startswith(prefix):
            href = href[len(prefix):]
            return urllib.parse.unquote(href)
    return href


def strip_html_url(url):
    if url.endswith('.html'):
        url = url[:-len('.html')]
    if url.endswith('.htm'):
        url = url[:-len('.htm')]
    if url.startswith('http://'):
        url = url[len('http://'):]
    if url.startswith('http://'):
        url = url[len('https://'):]
    if url.startswith('www.'):
        url = url[len('www.'):]
    return url


def normalize_and_russify_anchor_text(text):
    if text is not None:
        text = text.strip(' \n\t\r"').lower()
        text = " ".join(text.split()).replace("c", "с").replace("e", "е").replace("o", "о")
        return text
    return ""


def check_link_sitemap(link_info: TLinkInfo):
    text = normalize_and_russify_anchor_text(link_info.anchor_text)
    return text.startswith('карта сайта')


def check_anticorr_link_text(link_info: TLinkInfo):
    text = link_info.anchor_text.strip().lower()
    if text.find('антикоррупционная комиссия') != -1:
        return True

    if text.startswith(u'противодействие') or text.startswith(u'борьба') or text.startswith(u'нет'):
        return text.find("коррупц") != -1
    return False


def check_sub_page_or_iframe(link_info: TLinkInfo):
    if link_info.target_url is None:
        return False
    if link_info.tag_name is not None and link_info.tag_name.lower() == "iframe":
        return True
    parent = strip_html_url(link_info.source_url)
    subpage = strip_html_url(link_info.target_url)
    return subpage.startswith(parent)


def get_site_domain_wo_www(url):
    if not re.search(r'^[A-Za-z0-9+.\-]+://', url):
        url = 'http://{0}'.format(url)
    domain = urllib.parse.urlparse(url).netloc
    if domain.startswith('www.'):
        domain = domain[len('www.'):]
    return domain


def prepare_for_logging(s):
    if s is None:
        return ""
    s = s.translate(str.maketrans(
        {"\n": " ",
         "\t": " ",
         "\r": " "}))
    return s.strip()


def get_html_title(html):
    try:
        if soup.title is None:
            return ""
        return soup.title.string.strip(" \n\r\t")
    except Exception as err:
        return ""


def convert_timeout_to_seconds(s):
    if isinstance(s, int):
        return s
    seconds_per_unit = {"s": 1, "m": 60, "h": 3600}
    if s is None or len(s) == 0:
        return 0
    if seconds_per_unit.get(s[-1]) is not None:
        return int(s[:-1]) * seconds_per_unit[s[-1]]
    else:
        return int(s)



def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        print(ex)
        return False



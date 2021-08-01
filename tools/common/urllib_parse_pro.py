import urllib.parse
import re


def urlsplit_pro(url):
    url = re.sub(r'^(https?)://(/+)', r'\1://', url)  # https:////petushki.info -> http://petushki.info ->
    if not url.startswith('http') and not url.startswith('//') and url[1:10].find('://') == -1:
        url = "//" + url
    return urllib.parse.urlsplit(url)


def get_url_modifications(url: str):
    o = urlsplit_pro(url)
    if len(o.scheme) > 0:
        protocols = [o.scheme]
    else:
        protocols = ["http", "https"]
    if o.netloc.startswith("www."):
        with_www = [False] # already has www
    else:
        with_www = [True, False]
    for only_with_www in with_www:
        for protocol in protocols:
            host = o.netloc
            if only_with_www:
                host = "www." + host
            modified_url = urllib.parse.urlunsplit((protocol, host, o.path, o.query, o.fragment))
            yield modified_url

# get_web_site_identifier returns netloc  + url path without www
# for example http://www.aot.ru/some_page?aaa=1 -> aot.ru/some_page
def strip_scheme_and_query(url):
    if url.startswith("https"):
        url = url.replace(':443/', '/')
        if url.endswith(':443'):
            url = url[:-4]

    url = url.strip('/').lower()

    for p in ['http://', 'https://', "www."]:
        if url.startswith(p):
            url = url[len(p):]
    if TUrlUtf8Encode.is_idna_string(url):
        url = TUrlUtf8Encode.convert_url_from_idna(url)
    return url


def site_url_to_file_name(site_url: str):
    file_name = strip_scheme_and_query(site_url)
    file_name = re.sub('(:)(?=[0-9])', '_port_delim_', file_name)
    i = file_name.find('/')
    if i != -1:
        file_name = file_name[:i]
    assert len(file_name) > 0
    assert file_name.find('.') != -1
    return file_name


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


# get_site_domain_wo_www returns netloc without www
# for excample http://www.aot.ru -> aot.ru
# http://www.aot.ru/xxxx?aaa -> aot.ru
def get_site_domain_wo_www(url):
    if url is None or len(url) == 0:
        return ""

    if not re.search(r'^[A-Za-z0-9+.\-]+://', url):
        url = 'http://{0}'.format(url)
    domain = urlsplit_pro(url).netloc
    if domain.startswith('www.'):
        domain = domain[len('www.'):]
    return domain


class TUrlUtf8Encode:
    @staticmethod
    def is_idna_string(s):
        #1.xn----7sbam0ao3b.xn--p1ai
        return s.find("xn--") != -1

    @staticmethod
    def has_cyrillic(text):
        return bool(re.search('[Ёёа-яА-Я]', text))

    @staticmethod
    def to_idna(s):
        try:
            return s.encode('idna').decode('latin')
        except UnicodeError as err:
            #see     def test_idna_exception(self):
            if TUrlUtf8Encode.has_cyrillic(s):
                raise
            else:
                return s

    @staticmethod
    def from_idna(s):
        return s.encode('latin').decode('idna')

    @staticmethod
    def convert_if_idna(s):
        if TUrlUtf8Encode.is_idna_string(s):
            return TUrlUtf8Encode.from_idna(s)
        else:
            return s

    @staticmethod
    def convert_url_to_idna(url):
        o = urlsplit_pro(url)
        host = o.netloc
        if TUrlUtf8Encode.has_cyrillic(host):
            host = TUrlUtf8Encode.to_idna(host)
        url = urllib.parse.urlunsplit((o.scheme, host, o.path, o.query, o.fragment))
        return url

    @staticmethod
    def convert_url_from_idna(url):
        if not TUrlUtf8Encode.is_idna_string(url):
            return url
        o = urlsplit_pro(url)
        host = TUrlUtf8Encode.from_idna(o.netloc)
        s = urllib.parse.urlunsplit((o.scheme, host, o.path, o.query, o.fragment))
        if not url.startswith('//') and s.startswith('//'):
            s = s[2:]
        return s
import ssl
import sys
import urllib.parse
import urllib.request
import json
import hashlib
import shutil
from urllib.parse import urlparse, quote, urlunparse

# selenium staff
import os
from selenium import webdriver
import pyautogui
import time
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import staleness_of
FILE_CACHE_FOLDER="cached"

def download_html_with_selenium (url):
    # open page with selenium
    # (first need to download Chrome webdriver, or a firefox webdriver, etc)
    browser = webdriver.Firefox() #Chrome
    browser.minimize_window();
    browser.get(url)
    time.sleep(10)
    html = browser.page_source
    browser.close()
    browser.quit()
    return html


def find_links_with_selenium (url, check_text_func):
    browser = webdriver.Firefox() #Chrome
    #browser.minimize_window();
    browser.implicitly_wait(5)
    browser.get(url)
    time.sleep(6)
    elements = browser.find_elements_by_xpath('//button | //a')
    links = []
    for e in elements:
        if check_text_func('', e.text):
            e.click()
            time.sleep(6)
            browser.switch_to_window(browser.window_handles[-1])
            links.append ({'url':  browser.current_url, 'text': e.text.strip('\n\r\t ')})
            browser.switch_to_window(browser.window_handles[0])
    browser.quit()
    return links

def is_html_contents(info):
    content_type = info.get('Content-Type')
    return content_type.startswith('text')


def download_html_with_urllib (url):
    mvd = "https://" + u'мвд.рф'.encode('idna').decode('latin')
    url = url.replace('http://www.mvd.ru', mvd)
    o = list(urlparse(url)[:])
    o[2] = quote(o[2])
    url = urlunparse(o)
    #url = url.encode("utf8")
    context = ssl._create_unverified_context()
    req = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
    )
    data = ''
    info = {}
    print ("\turlopen..")
    with urllib.request.urlopen(req, context=context, timeout=20.0) as request:
        print("\treaddata...")
        data =  request.read()
        info = request.info()
    print("\tencoding..")
    try:
        if is_html_contents(info):
            data = data.decode('utf8', errors="ignore")
        return data, info
    except AttributeError:
        return (data, info)

def get_local_file_name_by_url(url):
    global FILE_CACHE_FOLDER
    localfile = url
    if localfile.startswith('http://'):
        localfile = localfile[7:]
    if localfile.startswith('https://'):
        localfile = localfile[8:]
    localfile = localfile.replace(':', '_')
    localfile = localfile.replace('/', '\\')
    localfile = localfile.replace('&', '_')
    localfile = localfile.replace('=', '_')
    localfile = localfile.replace('?', '_')
    if len(localfile) > 64:
        localfile = localfile[0:64] + "_" + hashlib.md5(url.encode('utf8',  errors="ignore")).hexdigest()
    localfile = os.path.join(FILE_CACHE_FOLDER, localfile)
    if not localfile.endswith('html') and not localfile.endswith('htm'):
        localfile += "/index.html"
    if not os.path.exists(os.path.dirname(localfile)):
        os.makedirs(os.path.dirname(localfile))
    return localfile

def build_temp_local_file(url):
    localfile = get_local_file_name_by_url(url)
    if not os.path.exists(localfile):
        return "";
    content_type = "text"
    info_file = localfile + ".headers"
    with open(info_file, "r", encoding="utf8") as inf:
        info = json.loads(inf.read())
        content_type = info['headers'].get('Content-Type', "text")
    dest_file = ""
    if url.endswith('.docx'):
        dest_file = "temp_file.docx"
    elif url.endswith('.doc'):
        dest_file = "temp_file.doc"
    elif url.endswith('.pdf'):
        dest_file = "temp_file.pdf"
    elif url.endswith('.rtf'):
        dest_file = "temp_file.pdf"
    elif content_type.startswith("text"):
        dest_file = "temp_file.html"
    elif content_type.startswith("application/vnd.openxmlformats-officedocument"):
        dest_file = "temp_file.docx"
    elif content_type.startswith("application/msword"):
        dest_file = "temp_file.doc"
    elif content_type.startswith("application/rtf"):
        dest_file = "temp_file.rtf"
    elif content_type.startswith("application/pdf"):
        dest_file = "temp_file.pdf"
    else:
        return ""
    dest_file = os.path.join(os.path.dirname(localfile), dest_file)
    dest_file = os.path.abspath(dest_file)
    shutil.copy(localfile, dest_file)
    return dest_file



def download_with_cache(url, use_selenium=False):
    localfile = get_local_file_name_by_url(url)
    info_file = localfile + ".headers"
    if os.path.exists(localfile):
        if not use_selenium:
            is_binary = False
            with open(info_file, "r", encoding="utf8") as inf:
                info = json.loads(inf.read())
                cached_headers = info['headers']
                is_binary = not is_html_contents(cached_headers)
                if info.get('input_url', '') != url:
                    sys.stderr.write("Warning! one cached local file for different urls {}!={}\n".format(url, info.get('input_url', '') ))
            if is_binary:
                return 'binary_data'
            else:
                with open(localfile, encoding="utf8") as f:
                    return f.read()
    if use_selenium:
        html = download_html_with_selenium(url)
        info = {'Content-Type': 'text/html'}
    else:
        html, info = download_html_with_urllib(url)
    if len(html) == 0:
        return html

    if is_html_contents(info):
        with open(localfile, "w", encoding="utf8") as f:
            f.write(html)
    else:
        with open(localfile, "wb") as f:
            f.write(html)

    if info is not None:
        with open(info_file, "w", encoding="utf8") as f:
            headers_and_url = {}
            headers_and_url['input_url'] = url
            headers_and_url['headers'] = dict(info._headers)
            f.write(json.dumps(headers_and_url, indent=4, ensure_ascii=False))
    if is_html_contents(info):
        return html
    else:
        return 'binary_data'

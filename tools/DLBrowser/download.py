import ssl
import urllib.parse
import urllib.request


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
    html = browser.page_source
    elements = browser.find_elements_by_xpath('//button | //a')
    links = []
    for e in elements:
        if check_text_func(e.text):
            e.click()
            time.sleep(6)
            browser.switch_to_window(browser.window_handles[-1])
            links.append ({'url':  browser.current_url, 'text': e.text.strip('\n\r\t ')})
            browser.switch_to_window(browser.window_handles[0])
        browser.close()
    return links


def download_html_with_urllib (url):
    mvd = "https://" + u'мвд.рф'.encode('idna').decode('latin')
    url = url.replace('http://www.mvd.ru', mvd)
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
    with urllib.request.urlopen(req, context=context) as request:
        data =  request.read()

    try:
        return data.decode('utf8', errors="ignore")
    except AttributeError:
        return data

def get_local_file_name_by_url(url):
    localfile = url
    localfile = localfile.replace(':', '_')
    localfile = localfile.replace('/', '_')

    localfile = os.path.join("data", localfile)
    if not localfile.endswith('html') and not localfile.endswith('htm'):
        localfile += "/index.html"
    if not os.path.exists(os.path.dirname(localfile)):
        os.makedirs(os.path.dirname(localfile))
    return localfile


def download_with_cache(url, use_selenium=False):
    localfile = get_local_file_name_by_url(url)
    if os.path.exists(localfile):
        if not use_selenium:
            with open(localfile, encoding="utf8") as f:
                return f.read()
    if use_selenium:
        html = download_html_with_selenium(url)
    else:
        html = download_html_with_urllib(url)
    if len(html) == 0:
        return html
    with open(localfile, "w", encoding="utf8") as f:
        f.write(html)
    return html

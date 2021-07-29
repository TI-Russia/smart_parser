from common.content_types import DEFAULT_HTML_EXTENSION
from common.html_parser import THtmlParser

import re
import hashlib
import os
import socket
import time
import subprocess


def normalize_whitespace(str):
    str = re.sub(r'\s+', ' ', str)
    str = str.strip()
    return str


def normalize_and_russify_anchor_text(text):
    if text is not None:
        text = text.strip(' \n\t\r"').lower()
        text = " ".join(text.split()).replace("c", "с").replace("e", "е").replace("o", "о")
        return text
    return ""


def prepare_for_logging(s):
    if s is None:
        return ""
    s = s.translate(str.maketrans(
        {"\n": " ",
         "\t": " ",
         "\r": " "}))
    return s.strip()


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


def build_dislosures_sha256_by_html(html_data):
    text = THtmlParser(html_data).get_plain_text()
    text_utf8 = text.encode("utf-8", errors="ignore")
    return hashlib.sha256(text_utf8).hexdigest()


def build_dislosures_sha256_by_file_data(file_data, file_extension):
    if file_extension == DEFAULT_HTML_EXTENSION:
        return build_dislosures_sha256_by_html(file_data)
    else:
        return hashlib.sha256(file_data).hexdigest()


def build_dislosures_sha256(file_path):
    _, file_extension = os.path.splitext(file_path)
    with open(file_path, "rb") as f:
        return build_dislosures_sha256_by_file_data(f.read(), file_extension)


def is_local_http_port_free(port, host='127.0.0.1'):
    for i in range(3):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            x = s.connect_ex((host, port))
            if x != 0:
                #cannot connect to the port, so it is open to start a new server
                s.close()
                return True
            print("wait 10 seconds till {}:{} is free (socket.connect_ex returned {})".format(host, port, x))
            time.sleep(10)
    return False


def run_with_timeout(args, timeout=20*60):
    p = subprocess.Popen(args, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    try:
        p.wait(timeout)
    except subprocess.TimeoutExpired:
        p.kill()


